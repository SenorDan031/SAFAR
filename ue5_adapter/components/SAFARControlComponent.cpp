#include "SAFARControlComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "ChaosVehicleMovementComponent.h"
#include "GameFramework/Actor.h"

USAFARControlComponent::USAFARControlComponent()
{
	PrimaryComponentTick.bCanEverTick = false;

	CurrentHUDStatus = TEXT("SAFAR: PASSIVE MONITORING");
	ThreatScore = 0.0f;
	bOverrideActive = false;

	InterventionThreshold = 0.70f;
	bEnforcePassiveDriverPrinciple = true;
	ReverseProtectionSpeedThresholdMps = 0.5f;
	bAllowSteeringOverride = false;

	VehicleMovementComponent = nullptr;
}

void USAFARControlComponent::BeginPlay()
{
	Super::BeginPlay();
	ResolveMovementComponent();
}

void USAFARControlComponent::ResolveMovementComponent()
{
	AActor* Owner = GetOwner();
	if (!Owner)
	{
		return;
	}

	VehicleMovementComponent = Owner->FindComponentByClass<UChaosWheeledVehicleMovementComponent>();
	if (!VehicleMovementComponent)
	{
		VehicleMovementComponent = Owner->FindComponentByClass<UChaosVehicleMovementComponent>();
	}

	if (UChaosWheeledVehicleMovementComponent* WheeledComp = Cast<UChaosWheeledVehicleMovementComponent>(VehicleMovementComponent))
	{
		// Disable Reverse-As-Brake so brake inputs never reverse the vehicle
		WheeledComp->TransmissionSetup.bReverseAsBrake = false;
		WheeledComp->SetHandbrakeInput(false);
	}
}

void USAFARControlComponent::ApplySafetyCommand(float Throttle, float Brake, float Steering, bool bEmergencyBrake)
{
	if (!VehicleMovementComponent)
	{
		ResolveMovementComponent();
		if (!VehicleMovementComponent)
		{
			return;
		}
	}

	bool bRequiresIntervention = (ThreatScore >= InterventionThreshold) || bEmergencyBrake || (Brake > 0.65f);

	if (bEnforcePassiveDriverPrinciple && !bRequiresIntervention)
	{
		if (bOverrideActive)
		{
			// Release override cleanly
			VehicleMovementComponent->SetHandbrakeInput(false);
		}
		bOverrideActive = false;
		return;
	}

	bOverrideActive = true;

	float CurrentForwardSpeedMps = FMath::Abs(VehicleMovementComponent->GetForwardSpeed()) / 100.0f;

	if (bEmergencyBrake || (Brake >= 0.85f))
	{
		VehicleMovementComponent->SetThrottleInput(0.0f);
		VehicleMovementComponent->SetBrakeInput(1.0f);

		if (CurrentForwardSpeedMps <= ReverseProtectionSpeedThresholdMps)
		{
			VehicleMovementComponent->SetHandbrakeInput(true);
		}
		else
		{
			VehicleMovementComponent->SetHandbrakeInput(false);
		}
	}
	else if (Brake > 0.10f)
	{
		VehicleMovementComponent->SetThrottleInput(FMath::Clamp(Throttle, 0.0f, 0.35f));
		VehicleMovementComponent->SetBrakeInput(FMath::Clamp(Brake, 0.0f, 1.0f));
		VehicleMovementComponent->SetHandbrakeInput(false);
	}
	else
	{
		VehicleMovementComponent->SetThrottleInput(FMath::Clamp(Throttle, 0.0f, 1.0f));
		VehicleMovementComponent->SetBrakeInput(0.0f);
		VehicleMovementComponent->SetHandbrakeInput(false);
	}

	if (bAllowSteeringOverride)
	{
		VehicleMovementComponent->SetSteeringInput(Steering);
	}
}
