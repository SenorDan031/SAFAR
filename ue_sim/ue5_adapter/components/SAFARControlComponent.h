#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SAFARControlComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;
class UChaosVehicleMovementComponent;

/**
 * SAFARControlComponent
 * Applies structured control decisions (Throttle, Brake, Steering, Handbrake)
 * directly into the Chaos Vehicle Movement Component of the host vehicle.
 * Enforces the Passive Driver Principle and Anti-Roll Reverse Protection.
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARControlComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARControlComponent();

	virtual void BeginPlay() override;

	/**
	 * Core Actuation Function: Routes safety commands into Chaos Vehicle movement.
	 */
	UFUNCTION(BlueprintCallable, Category = "SAFAR Control")
	void ApplySafetyCommand(float Throttle, float Brake, float Steering, bool bEmergencyBrake);

	// Telemetry & HUD State
	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	FString CurrentHUDStatus;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	float ThreatScore;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	bool bOverrideActive;

	// Configuration
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Safety Policy", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float InterventionThreshold = 0.70f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Safety Policy")
	bool bEnforcePassiveDriverPrinciple = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Safety Policy")
	float ReverseProtectionSpeedThresholdMps = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Safety Policy")
	bool bAllowSteeringOverride = false; // Reserved for Future Autonomous Emergency Steering (AES)

private:
	UPROPERTY()
	TObjectPtr<UChaosVehicleMovementComponent> VehicleMovementComponent;

	void ResolveMovementComponent();
};
