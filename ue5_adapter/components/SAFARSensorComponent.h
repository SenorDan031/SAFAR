#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/SceneCaptureComponent2D.h"
#include "HAL/CriticalSection.h"
#include "SAFARSensorComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UChaosVehicleMovementComponent;

/**
 * Structure containing thread-safe captured frame and vehicle IMU telemetry.
 */
struct FSAFARFrameData
{
	uint32 FrameId = 0;
	int64 TimestampUs = 0;
	float EgoSpeedMps = 0.0f;
	float EgoHeadingDeg = 0.0f;
	FString ImageFormat = TEXT("jpeg");
	TArray<uint8> EncodedImageBytes;
	bool bIsValid = false;
};

/**
 * SAFARSensorComponent
 * Attached to Chaos Vehicle Pawn to capture:
 * - Front, Left, and Right Virtual Cameras (SceneCaptureComponent2D)
 * - Vehicle State & IMU Telemetry (Position, Rotation, Velocity, Speed, Acceleration)
 * - Encodes frames as JPEG/RGB with decoupled configurable FPS
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARSensorComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARSensorComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	// Virtual Scene Capture Camera Components
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* FrontCameraComponent;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* LeftCameraComponent;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* RightCameraComponent;

	// Real-Time Vehicle IMU Telemetry
	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	FVector VehicleVelocity;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	float VehicleSpeedKmh;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	FVector VehicleAcceleration;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	float VehicleHeadingDeg;

	// Capture Configuration
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Capture Config", meta = (ClampMin = "1.0", ClampMax = "120.0"))
	float TargetCaptureFPS = 30.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Capture Config", meta = (ClampMin = "10", ClampMax = "100"))
	int32 JPEGCompressionQuality = 80;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Capture Config")
	bool bAutoFindCamerasOnBeginPlay = true;

	/** Thread-safe method to retrieve the latest captured and encoded frame */
	bool GetLatestFrameData(FSAFARFrameData& OutFrameData);

protected:
	void CaptureAndEncodeFrontCamera();
	void UpdateIMUTelemetry(float DeltaTime);

private:
	UPROPERTY()
	TObjectPtr<UChaosVehicleMovementComponent> CachedMovementComponent;

	FVector PreviousVelocity;
	float CaptureAccumulator;
	uint32 GlobalFrameCounter;

	FCriticalSection FrameDataLock;
	FSAFARFrameData LatestFrameData;

	TArray<FColor> RawPixelBuffer;
};
