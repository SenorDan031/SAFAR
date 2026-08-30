#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SAFARSensorComponent.generated.h"

/**
 * SAFARSensorComponent
 * Attached to BP_VehicleAdvSportsCar to capture:
 * - Front, Left, and Right Virtual Cameras (SceneCaptureComponent2D)
 * - Vehicle State & IMU Telemetry (Position, Rotation, Velocity, Speed, Acceleration)
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARSensorComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARSensorComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* FrontCameraComponent;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* LeftCameraComponent;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	class USceneCaptureComponent2D* RightCameraComponent;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	FVector VehicleVelocity;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	float VehicleSpeedKmh;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR IMU")
	FVector VehicleAcceleration;
};
