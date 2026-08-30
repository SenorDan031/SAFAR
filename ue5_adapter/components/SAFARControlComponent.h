#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SAFARControlComponent.generated.h"

/**
 * SAFARControlComponent
 * Applies structured control decisions (Throttle, Brake, Steering, Handbrake)
 * directly into the Chaos Vehicle Movement Component of the host vehicle.
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARControlComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARControlComponent();

	virtual void BeginPlay() override;

	UFUNCTION(BlueprintCallable, Category = "SAFAR Control")
	void ApplySafetyCommand(float Throttle, float Brake, float Steering, bool bEmergencyBrake);

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	FString CurrentHUDStatus;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	float ThreatScore;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Telemetry")
	bool bOverrideActive;
};
