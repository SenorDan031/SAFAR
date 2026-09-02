#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "SAFARVehiclePawn.generated.h"

class USpringArmComponent;
class UCameraComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
class USAFARSensorComponent;
class USAFARCommunicationComponent;
class USAFARControlComponent;

/**
 * ASAFARVehiclePawn
 * Chaos Wheeled Vehicle Pawn pre-configured with SAFAR Autonomous Safety Intelligence:
 * - Front Virtual Camera (SceneCaptureComponent2D)
 * - Sensor Component (Virtual Camera Grabber + IMU)
 * - Communication Component (TCP 9001 Streamer + UDP 9003 Receiver)
 * - Control Component (Actuator Overrides & Reverse-Protection)
 */
UCLASS()
class ASAFARVehiclePawn : public AWheeledVehiclePawn
{
	GENERATED_BODY()

public:
	ASAFARVehiclePawn(const FObjectInitializer& ObjectInitializer);

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> FollowCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SAFAR Sensors")
	TObjectPtr<USceneCaptureComponent2D> FrontSceneCapture;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Sensors")
	TObjectPtr<UTextureRenderTarget2D> FrontCameraRenderTarget;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SAFAR Subsystems")
	TObjectPtr<USAFARSensorComponent> SAFARSensor;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SAFAR Subsystems")
	TObjectPtr<USAFARCommunicationComponent> SAFARCommunication;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SAFAR Subsystems")
	TObjectPtr<USAFARControlComponent> SAFARControl;

protected:
	void MoveForward(float Val);
	void MoveRight(float Val);
	void HandbrakePressed();
	void HandbrakeReleased();
};
