#include "SAFARCommunicationComponent.h"
#include "SAFARSensorComponent.h"
#include "SAFARControlComponent.h"
#include "SocketSubsystem.h"
#include "IPAddress.h"
#include "Common/TcpSocketBuilder.h"
#include "Common/UdpSocketBuilder.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Dom/JsonObject.h"
#include "Async/Async.h"
#include "HAL/PlatformProcess.h"

// ============================================================================
// FSAFARTcpStreamerWorker Implementation
// ============================================================================

FSAFARTcpStreamerWorker::FSAFARTcpStreamerWorker(
	const FString& InHost,
	int32 InPort,
	USAFARSensorComponent* InSensorComp,
	float InTargetFPS
)
	: ServerHost(InHost)
	, ServerPort(InPort)
	, SensorComponent(InSensorComp)
	, TargetFPS(InTargetFPS)
	, ClientSocket(nullptr)
	, bRunning(false)
	, bIsConnected(false)
	, LastSentFrameId(0)
{
}

FSAFARTcpStreamerWorker::~FSAFARTcpStreamerWorker()
{
	CloseSocket();
}

bool FSAFARTcpStreamerWorker::Init()
{
	bRunning = true;
	return true;
}

uint32 FSAFARTcpStreamerWorker::Run()
{
	float SleepIntervalSeconds = (TargetFPS > 0.0f) ? (1.0f / TargetFPS) : (1.0f / 30.0f);

	while (bRunning)
	{
		// 1. Maintain Connection
		if (!bIsConnected || !ClientSocket)
		{
			if (!ConnectToPerceptionServer())
			{
				// Backoff before retry
				FPlatformProcess::Sleep(1.0f);
				continue;
			}
		}

		// 2. Fetch Latest Sensor Frame
		if (SensorComponent.IsValid())
		{
			FSAFARFrameData FrameData;
			if (SensorComponent->GetLatestFrameData(FrameData))
			{
				if (FrameData.FrameId != LastSentFrameId && FrameData.EncodedImageBytes.Num() > 0)
				{
					if (SendSFRMPacket(FrameData))
					{
						LastSentFrameId = FrameData.FrameId;
					}
					else
					{
						// Socket send failure -> reconnect on next iteration
						CloseSocket();
					}
				}
			}
		}

		FPlatformProcess::Sleep(SleepIntervalSeconds * 0.5f);
	}

	CloseSocket();
	return 0;
}

void FSAFARTcpStreamerWorker::Stop()
{
	bRunning = false;
	CloseSocket();
}

void FSAFARTcpStreamerWorker::Exit()
{
	bIsConnected = false;
}

bool FSAFARTcpStreamerWorker::ConnectToPerceptionServer()
{
	CloseSocket();

	ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (!SocketSubsystem)
	{
		return false;
	}

	TSharedRef<FInternetAddr> TargetAddr = SocketSubsystem->CreateInternetAddr();
	bool bIsValidIp = false;
	TargetAddr->SetIp(*ServerHost, bIsValidIp);
	TargetAddr->SetPort(ServerPort);

	if (!bIsValidIp)
	{
		return false;
	}

	ClientSocket = FTcpSocketBuilder(TEXT("SAFAR_Perception_TCP_Client"))
		.AsBlocking()
		.WithSendBufferSize(2 * 1024 * 1024)
		.Build();

	if (!ClientSocket)
	{
		return false;
	}

	if (!ClientSocket->Connect(*TargetAddr))
	{
		CloseSocket();
		return false;
	}

	bIsConnected = true;
	return true;
}

bool FSAFARTcpStreamerWorker::SendSFRMPacket(const FSAFARFrameData& FrameData)
{
	if (!ClientSocket || !bIsConnected)
	{
		return false;
	}

	// 1. Construct Metadata JSON String
	FString MetaJson = FString::Printf(
		TEXT("{\"timestamp_us\":%lld,\"frame_id\":%u,\"ego_speed_mps\":%.2f,\"ego_heading_deg\":%.2f,\"image_format\":\"%s\",\"image_bytes_len\":%d}"),
		FrameData.TimestampUs,
		FrameData.FrameId,
		FrameData.EgoSpeedMps,
		FrameData.EgoHeadingDeg,
		*FrameData.ImageFormat,
		FrameData.EncodedImageBytes.Num()
	);

	FTCHARToUTF8 Converter(*MetaJson);
	const int32 MetaJsonBytesLen = Converter.Length(); // Excludes null-terminator

	// Payload is: MetaJson + '\0' + EncodedImageBytes
	const uint32 TotalPayloadLength = static_cast<uint32>(MetaJsonBytesLen + 1 + FrameData.EncodedImageBytes.Num());

	// 2. Construct 8-byte Header: Magic "SFRM" + 4-byte Big-Endian Length
	uint8 Header[8];
	Header[0] = 'S';
	Header[1] = 'F';
	Header[2] = 'R';
	Header[3] = 'M';

	uint32 BigEndianLen = 0;
#if PLATFORM_LITTLE_ENDIAN
	BigEndianLen = BYTESWAP_ORDER32(TotalPayloadLength);
#else
	BigEndianLen = TotalPayloadLength;
#endif

	FMemory::Memcpy(&Header[4], &BigEndianLen, sizeof(uint32));

	// 3. Assemble and Send Buffer
	TArray<uint8> FullPacket;
	FullPacket.Reserve(8 + TotalPayloadLength);
	FullPacket.Append(Header, 8);
	FullPacket.Append((const uint8*)Converter.Get(), MetaJsonBytesLen);
	FullPacket.Add(0); // Null terminator
	FullPacket.Append(FrameData.EncodedImageBytes);

	int32 BytesSent = 0;
	bool bSuccess = ClientSocket->Send(FullPacket.GetData(), FullPacket.Num(), BytesSent);

	return bSuccess && (BytesSent == FullPacket.Num());
}

void FSAFARTcpStreamerWorker::CloseSocket()
{
	bIsConnected = false;
	if (ClientSocket)
	{
		ClientSocket->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ClientSocket);
		ClientSocket = nullptr;
	}
}

// ============================================================================
// USAFARCommunicationComponent Implementation
// ============================================================================

USAFARCommunicationComponent::USAFARCommunicationComponent()
{
	PrimaryComponentTick.bCanEverTick = false;

	PerceptionHost = TEXT("127.0.0.1");
	PerceptionPort = 9001;
	ControlPort = 9003;

	bConnectedToCore = false;
	bConnectedToPerception = false;
	PacketsReceivedCount = 0;

	TcpWorker = nullptr;
	TcpWorkerThread = nullptr;
	UdpSocket = nullptr;
}

void USAFARCommunicationComponent::BeginPlay()
{
	Super::BeginPlay();

	AActor* Owner = GetOwner();
	if (Owner)
	{
		SensorComponent = Owner->FindComponentByClass<USAFARSensorComponent>();
		ControlComponent = Owner->FindComponentByClass<USAFARControlComponent>();
	}

	// 1. Start Non-Blocking UDP Control Listener on Port 9003
	StartUdpReceiver();

	// 2. Start Non-Blocking TCP Perception Streamer on Port 9001
	StartTcpStreamer();
}

void USAFARCommunicationComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopTcpStreamer();
	StopUdpReceiver();

	Super::EndPlay(EndPlayReason);
}

void USAFARCommunicationComponent::StartTcpStreamer()
{
	if (!SensorComponent)
	{
		return;
	}

	StopTcpStreamer();

	TcpWorker = new FSAFARTcpStreamerWorker(
		PerceptionHost,
		PerceptionPort,
		SensorComponent,
		SensorComponent->TargetCaptureFPS
	);

	TcpWorkerThread = FRunnableThread::Create(
		TcpWorker,
		TEXT("SAFAR_TcpStreamerThread"),
		0,
		TPri_BelowNormal
	);
}

void USAFARCommunicationComponent::StopTcpStreamer()
{
	if (TcpWorkerThread)
	{
		TcpWorkerThread->Kill(true);
		delete TcpWorkerThread;
		TcpWorkerThread = nullptr;
	}

	if (TcpWorker)
	{
		delete TcpWorker;
		TcpWorker = nullptr;
	}

	bConnectedToPerception = false;
}

void USAFARCommunicationComponent::StartUdpReceiver()
{
	StopUdpReceiver();

	FIPv4Endpoint Endpoint(FIPv4Address::Any, ControlPort);

	UdpSocket = FUdpSocketBuilder(TEXT("SAFAR_Control_UDP_Socket"))
		.AsNonBlocking()
		.AsReusable()
		.BoundToEndpoint(Endpoint)
		.WithReceiveBufferSize(1024 * 1024)
		.Build();

	if (UdpSocket)
	{
		UdpReceiver = MakeShared<FUdpSocketReceiver>(
			UdpSocket,
			FTimespan::FromMilliseconds(20),
			TEXT("SAFAR_UdpReceiverThread")
		);

		UdpReceiver->OnDataReceived().BindUObject(this, &USAFARCommunicationComponent::HandleControlPacketReceived);
		UdpReceiver->Start();
	}
}

void USAFARCommunicationComponent::StopUdpReceiver()
{
	if (UdpReceiver.IsValid())
	{
		UdpReceiver->Stop();
		UdpReceiver.Reset();
	}

	if (UdpSocket)
	{
		UdpSocket->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(UdpSocket);
		UdpSocket = nullptr;
	}

	bConnectedToCore = false;
}

void USAFARCommunicationComponent::HandleControlPacketReceived(const FArrayReaderPtr& ArrayReaderPtr, const FIPv4Endpoint& Endpoint)
{
	if (!ArrayReaderPtr.IsValid() || ArrayReaderPtr->Num() == 0)
	{
		return;
	}

	// Convert raw UTF-8 bytes to FString
	TArray<uint8> DataCopy = *ArrayReaderPtr;
	DataCopy.Add(0); // Null terminate for safety

	FString JsonString = UTF8_TO_TCHAR(reinterpret_cast<const char*>(DataCopy.GetData()));
	ParseAndDispatchControlJson(JsonString);
}

void USAFARCommunicationComponent::ParseAndDispatchControlJson(const FString& JsonString)
{
	TSharedPtr<FJsonObject> JsonObject;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);

	if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
	{
		return;
	}

	bConnectedToCore = true;
	PacketsReceivedCount++;

	// Extract Threat Score
	float ThreatScore = 0.0f;
	if (JsonObject->HasField(TEXT("threat_score")))
	{
		ThreatScore = static_cast<float>(JsonObject->GetNumberField(TEXT("threat_score")));
	}

	// Extract Decision Action
	FString DecisionStr = TEXT("CONTINUE");
	if (JsonObject->HasField(TEXT("decision")))
	{
		DecisionStr = JsonObject->GetStringField(TEXT("decision"));
	}

	// Extract Control Sub-object or Top-level fields
	float Throttle = 1.0f;
	float Brake = 0.0f;
	float Steering = 0.0f;
	bool bEmergencyBrake = false;

	if (JsonObject->HasTypedField<EJson::Object>(TEXT("control")))
	{
		TSharedPtr<FJsonObject> CtrlObj = JsonObject->GetObjectField(TEXT("control"));
		Throttle = static_cast<float>(CtrlObj->GetNumberField(TEXT("throttle")));
		Brake = static_cast<float>(CtrlObj->GetNumberField(TEXT("brake")));
		Steering = static_cast<float>(CtrlObj->GetNumberField(TEXT("steering")));
		if (CtrlObj->HasField(TEXT("emergency_stop")))
		{
			bEmergencyBrake = CtrlObj->GetBoolField(TEXT("emergency_stop"));
		}
		else if (CtrlObj->HasField(TEXT("emergency_brake")))
		{
			bEmergencyBrake = CtrlObj->GetBoolField(TEXT("emergency_brake"));
		}
	}
	else
	{
		// Top-level fallbacks conforming to protocols.md
		if (JsonObject->HasField(TEXT("throttle"))) Throttle = static_cast<float>(JsonObject->GetNumberField(TEXT("throttle")));
		if (JsonObject->HasField(TEXT("brake"))) Brake = static_cast<float>(JsonObject->GetNumberField(TEXT("brake")));
		if (JsonObject->HasField(TEXT("steering"))) Steering = static_cast<float>(JsonObject->GetNumberField(TEXT("steering")));
		if (JsonObject->HasField(TEXT("emergency_brake"))) bEmergencyBrake = JsonObject->GetBoolField(TEXT("emergency_brake"));
	}

	// Extract HUD Status Message
	FString HUDMsg = TEXT("");
	if (JsonObject->HasField(TEXT("hud_message")))
	{
		HUDMsg = JsonObject->GetStringField(TEXT("hud_message"));
	}
	else if (JsonObject->HasField(TEXT("hud_status")))
	{
		HUDMsg = JsonObject->GetStringField(TEXT("hud_status"));
	}

	// Forward to Control Component on Game Thread
	if (ControlComponent)
	{
		AsyncTask(ENamedThreads::GameThread, [this, Throttle, Brake, Steering, bEmergencyBrake, ThreatScore, HUDMsg]()
		{
			if (ControlComponent)
			{
				ControlComponent->ThreatScore = ThreatScore;
				ControlComponent->CurrentHUDStatus = HUDMsg;
				ControlComponent->ApplySafetyCommand(Throttle, Brake, Steering, bEmergencyBrake);
			}
		});
	}
}
