#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HAL/Runnable.h"
#include "HAL/RunnableThread.h"
#include "HAL/ThreadSafeBool.h"
#include "Sockets.h"
#include "Common/UdpSocketReceiver.h"
#include "SAFARCommunicationComponent.generated.h"

class USAFARSensorComponent;
class USAFARControlComponent;

/**
 * Worker thread for non-blocking TCP sensor streaming to Python Perception (Port 9001).
 */
class FSAFARTcpStreamerWorker : public FRunnable
{
public:
	FSAFARTcpStreamerWorker(
		const FString& InHost,
		int32 InPort,
		USAFARSensorComponent* InSensorComp,
		float InTargetFPS = 30.0f
	);
	virtual ~FSAFARTcpStreamerWorker() override;

	virtual bool Init() override;
	virtual uint32 Run() override;
	virtual void Stop() override;
	virtual void Exit() override;

	bool IsConnected() const { return bIsConnected; }

private:
	bool ConnectToPerceptionServer();
	bool SendSFRMPacket(const struct FSAFARFrameData& FrameData);
	void CloseSocket();

	FString ServerHost;
	int32 ServerPort;
	TWeakObjectPtr<USAFARSensorComponent> SensorComponent;
	float TargetFPS;

	FSocket* ClientSocket;
	FThreadSafeBool bRunning;
	FThreadSafeBool bIsConnected;
	uint32 LastSentFrameId;
};

/**
 * SAFARCommunicationComponent
 * Manages low-latency UDP/TCP communication between Unreal Engine, Python, and C++ SAFAR Core.
 * - TCP Client (Port 9001): Streams SFRM framed virtual camera images & IMU to Python.
 * - UDP Listener (Port 9003): Receives real-time safety control decisions & HUD status from C++ Core.
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARCommunicationComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARCommunicationComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// Configuration
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Network")
	FString PerceptionHost = TEXT("127.0.0.1");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Network")
	int32 PerceptionPort = 9001;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Network")
	int32 ControlPort = 9003;

	// Telemetry & Status
	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Network")
	bool bConnectedToCore = false;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Network")
	bool bConnectedToPerception = false;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Network")
	int32 PacketsReceivedCount = 0;

private:
	void StartTcpStreamer();
	void StopTcpStreamer();

	void StartUdpReceiver();
	void StopUdpReceiver();

	void HandleControlPacketReceived(const FArrayReaderPtr& ArrayReaderPtr, const FIPv4Endpoint& Endpoint);
	void ParseAndDispatchControlJson(const FString& JsonString);

	UPROPERTY()
	TObjectPtr<USAFARSensorComponent> SensorComponent;

	UPROPERTY()
	TObjectPtr<USAFARControlComponent> ControlComponent;

	// TCP Streamer Thread
	FSAFARTcpStreamerWorker* TcpWorker;
	FRunnableThread* TcpWorkerThread;

	// UDP Receiver
	FSocket* UdpSocket;
	TSharedPtr<FUdpSocketReceiver> UdpReceiver;
};
