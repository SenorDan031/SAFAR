#include "SAFARSensorComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "TextureResource.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Modules/ModuleManager.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "ChaosVehicleMovementComponent.h"
#include "GameFramework/Actor.h"
#include "HAL/PlatformTime.h"
#include "Misc/DateTime.h"

USAFARSensorComponent::USAFARSensorComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;

	FrontCameraComponent = nullptr;
	LeftCameraComponent = nullptr;
	RightCameraComponent = nullptr;

	VehicleVelocity = FVector::ZeroVector;
	VehicleSpeedKmh = 0.0f;
	VehicleAcceleration = FVector::ZeroVector;
	VehicleHeadingDeg = 0.0f;

	TargetCaptureFPS = 30.0f;
	JPEGCompressionQuality = 80;
	bAutoFindCamerasOnBeginPlay = true;

	PreviousVelocity = FVector::ZeroVector;
	CaptureAccumulator = 0.0f;
	GlobalFrameCounter = 0;
}

void USAFARSensorComponent::BeginPlay()
{
	Super::BeginPlay();

	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return;
	}

	// 1. Resolve Chaos Vehicle Movement Component
	CachedMovementComponent = Owner->FindComponentByClass<UChaosWheeledVehicleMovementComponent>();
	if (!CachedMovementComponent)
	{
		CachedMovementComponent = Owner->FindComponentByClass<UChaosVehicleMovementComponent>();
	}

	// 2. Auto-discover camera components if not manually assigned
	if (bAutoFindCamerasOnBeginPlay)
	{
		TArray<USceneCaptureComponent2D*> CaptureComps;
		Owner->GetComponents<USceneCaptureComponent2D>(CaptureComps);

		for (USceneCaptureComponent2D* Comp : CaptureComps)
		{
			FString CompName = Comp->GetName().ToLower();
			if (!FrontCameraComponent && (CompName.Contains(TEXT("front")) || CompName.Contains(TEXT("camera"))))
			{
				FrontCameraComponent = Comp;
			}
			else if (!LeftCameraComponent && CompName.Contains(TEXT("left")))
			{
				LeftCameraComponent = Comp;
			}
			else if (!RightCameraComponent && CompName.Contains(TEXT("right")))
			{
				RightCameraComponent = Comp;
			}
		}
	}

	// 3. Ensure Front Camera has appropriate capture flags
	if (FrontCameraComponent)
	{
		FrontCameraComponent->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
		FrontCameraComponent->bCaptureEveryFrame = false; // We trigger capture manually for precise FPS decoupling
		FrontCameraComponent->bCaptureOnMovement = false;
	}
}

void USAFARSensorComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	// 1. Update Real-Time IMU Telemetry
	UpdateIMUTelemetry(DeltaTime);

	// 2. Decoupled Frame Rate Capture
	float CaptureInterval = (TargetCaptureFPS > 0.0f) ? (1.0f / TargetCaptureFPS) : (1.0f / 30.0f);
	CaptureAccumulator += DeltaTime;

	if (CaptureAccumulator >= CaptureInterval)
	{
		CaptureAccumulator = FMath::Fmod(CaptureAccumulator, CaptureInterval);
		CaptureAndEncodeFrontCamera();
	}
}

void USAFARSensorComponent::UpdateIMUTelemetry(float DeltaTime)
{
	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return;
	}

	// Extract Metric Velocity & Speed
	FVector CurrentVelocityCmS = Owner->GetVelocity();
	VehicleVelocity = CurrentVelocityCmS / 100.0f; // Convert cm/s to m/s
	VehicleSpeedKmh = (CurrentVelocityCmS.Size() / 100.0f) * 3.6f;

	// Calculate Linear Acceleration
	float SafeDeltaTime = FMath::Max(0.0001f, DeltaTime);
	VehicleAcceleration = (VehicleVelocity - PreviousVelocity) / SafeDeltaTime;
	PreviousVelocity = VehicleVelocity;

	// Vehicle Compass Heading in Degrees
	VehicleHeadingDeg = Owner->GetActorRotation().Yaw;
}

void USAFARSensorComponent::CaptureAndEncodeFrontCamera()
{
	if (!FrontCameraComponent || !FrontCameraComponent->TextureTarget)
	{
		return;
	}

	// Trigger immediate scene capture
	FrontCameraComponent->CaptureScene();

	UTextureRenderTarget2D* RenderTarget = FrontCameraComponent->TextureTarget;
	FTextureRenderTargetResource* RTResource = RenderTarget->GameThread_GetRenderTargetResource();
	if (!RTResource)
	{
		return;
	}

	int32 Width = RenderTarget->SizeX;
	int32 Height = RenderTarget->SizeY;
	if (Width <= 0 || Height <= 0)
	{
		return;
	}

	// Read render target pixels (BGRA format)
	RawPixelBuffer.Reset();
	if (!RTResource->ReadPixels(RawPixelBuffer))
	{
		return;
	}

	if (RawPixelBuffer.Num() == 0)
	{
		return;
	}

	// Compress pixels to JPEG using Unreal's ImageWrapper
	IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(FName("ImageWrapper"));
	TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::JPEG);

	if (ImageWrapper.IsValid())
	{
		if (ImageWrapper->SetRaw(RawPixelBuffer.GetData(), RawPixelBuffer.Num() * sizeof(FColor), Width, Height, ERGBFormat::BGRA, 8))
		{
			const TArray64<uint8>& Compressed64 = ImageWrapper->GetCompressed(JPEGCompressionQuality);
			if (Compressed64.Num() > 0)
			{
				int64 CurrentTimeUs = FDateTime::UtcNow().ToUnixTimestamp() * 1000000 + FDateTime::UtcNow().GetMillisecond() * 1000;
				GlobalFrameCounter++;

				FScopeLock Lock(&FrameDataLock);
				LatestFrameData.FrameId = GlobalFrameCounter;
				LatestFrameData.TimestampUs = CurrentTimeUs;
				LatestFrameData.EgoSpeedMps = VehicleVelocity.Size();
				LatestFrameData.EgoHeadingDeg = VehicleHeadingDeg;
				LatestFrameData.ImageFormat = TEXT("jpeg");
				LatestFrameData.EncodedImageBytes.SetNumUninitialized(Compressed64.Num());
				FMemory::Memcpy(LatestFrameData.EncodedImageBytes.GetData(), Compressed64.GetData(), Compressed64.Num());
				LatestFrameData.bIsValid = true;
			}
		}
	}
}

bool USAFARSensorComponent::GetLatestFrameData(FSAFARFrameData& OutFrameData)
{
	FScopeLock Lock(&FrameDataLock);
	if (!LatestFrameData.bIsValid)
	{
		return false;
	}

	OutFrameData = LatestFrameData;
	return true;
}
