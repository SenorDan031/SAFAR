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

	// 1. Evaluate Passive Driver Principle
	// Player controls remain authoritative until ThreatScore crosses intervention threshold or emergency brake triggers
	bool bRequiresIntervention = (ThreatScore >= InterventionThreshold) || bEmergencyBrake || (Brake > 0.65f);

	if (bEnforcePassiveDriverPrinciple && !bRequiresIntervention)
	{
		// Passive State: Do NOT override player inputs
		bOverrideActive = false;
		return;
	}

	// 2. Autonomous Safety Override Active
	bOverrideActive = true;

	// Extract Current Ego Speed in m/s
	float CurrentForwardSpeedMps = FMath::Abs(VehicleMovementComponent->GetForwardSpeed()) / 100.0f;

	// 3. Actuate Throttle & Brake with Reverse-Protection Anti-Roll Logic
	if (bEmergencyBrake || (Brake >= 0.85f))
	{
		// Full Emergency Stop requested
		VehicleMovementComponent->SetThrottleInput(0.0f);
		VehicleMovementComponent->SetBrakeInput(1.0f);

		if (CurrentForwardSpeedMps <= ReverseProtectionSpeedThresholdMps)
		{
			// Vehicle has come to a stop -> Lock Handbrake to prevent reverse roll / idle creep
			VehicleMovementComponent->SetHandbrakeInput(true);
		}
		else
		{
			// Vehicle is actively decelerating above 0.5 m/s -> Service brake only
			VehicleMovementComponent->SetHandbrakeInput(false);
		}
	}
	else if (Brake > 0.10f)
	{
		// Controlled service braking / deceleration
		VehicleMovementComponent->SetThrottleInput(FMath::Clamp(Throttle, 0.0f, 0.35f));
		VehicleMovementComponent->SetBrakeInput(FMath::Clamp(Brake, 0.0f, 1.0f));
		VehicleMovementComponent->SetHandbrakeInput(false);
	}
	else
	{
		// Throttle moderation
		VehicleMovementComponent->SetThrottleInput(FMath::Clamp(Throttle, 0.0f, 1.0f));
		VehicleMovementComponent->SetBrakeInput(0.0f);
		VehicleMovementComponent->SetHandbrakeInput(false);
	}

	// 4. Autonomous Emergency Steering (AES) Stub
	if (bAllowSteeringOverride)
	{
		// Future AES Phase: Apply evasive corridor steering
		VehicleMovementComponent->SetSteeringInput(Steering);
	}
}
