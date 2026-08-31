#include "SAFARVehiclePawn.h"
#include "SAFARSensorComponent.h"
#include "SAFARCommunicationComponent.h"
#include "SAFARControlComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ChaosWheeledVehicleMovementComponent.h"

ASAFARVehiclePawn::ASAFARVehiclePawn(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(RootComponent);
	SpringArm->TargetArmLength = 550.0f;
	SpringArm->SocketOffset = FVector(0.0f, 0.0f, 150.0f);
	SpringArm->bUsePawnControlRotation = false;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	FrontSceneCapture = CreateDefaultSubobject<USceneCaptureComponent2D>(TEXT("FrontSceneCapture"));
	FrontSceneCapture->SetupAttachment(RootComponent);
	FrontSceneCapture->SetRelativeLocation(FVector(180.0f, 0.0f, 120.0f));
	FrontSceneCapture->FOVAngle = 90.0f;
	FrontSceneCapture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	FrontSceneCapture->bCaptureEveryFrame = false;
	FrontSceneCapture->bCaptureOnMovement = false;

	SAFARSensor = CreateDefaultSubobject<USAFARSensorComponent>(TEXT("SAFARSensor"));
	SAFARSensor->FrontCameraComponent = FrontSceneCapture;

	SAFARCommunication = CreateDefaultSubobject<USAFARCommunicationComponent>(TEXT("SAFARCommunication"));
	SAFARControl = CreateDefaultSubobject<USAFARControlComponent>(TEXT("SAFARControl"));
}

void ASAFARVehiclePawn::BeginPlay()
{
	Super::BeginPlay();

	if (!FrontCameraRenderTarget)
	{
		FrontCameraRenderTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("RT_FrontCamera"));
		if (FrontCameraRenderTarget)
		{
			FrontCameraRenderTarget->InitAutoFormat(640, 480);
			FrontCameraRenderTarget->UpdateResourceImmediate(true);
		}
	}

	if (FrontSceneCapture && FrontCameraRenderTarget)
	{
		FrontSceneCapture->TextureTarget = FrontCameraRenderTarget;
		SAFARSensor->FrontCameraComponent = FrontSceneCapture;
	}
}

void ASAFARVehiclePawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
}

void ASAFARVehiclePawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	if (PlayerInputComponent)
	{
		PlayerInputComponent->BindAxis(TEXT("MoveForward"), this, &ASAFARVehiclePawn::MoveForward);
		PlayerInputComponent->BindAxis(TEXT("MoveRight"), this, &ASAFARVehiclePawn::MoveRight);
		PlayerInputComponent->BindAction(TEXT("Handbrake"), IE_Pressed, this, &ASAFARVehiclePawn::HandbrakePressed);
		PlayerInputComponent->BindAction(TEXT("Handbrake"), IE_Released, this, &ASAFARVehiclePawn::HandbrakeReleased);
	}
}

void ASAFARVehiclePawn::MoveForward(float Val)
{
	UChaosWheeledVehicleMovementComponent* Movement = Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	if (!Movement || (SAFARControl && SAFARControl->bOverrideActive))
	{
		return;
	}

	if (Val >= 0.0f)
	{
		Movement->SetThrottleInput(Val);
		Movement->SetBrakeInput(0.0f);
	}
	else
	{
		Movement->SetThrottleInput(0.0f);
		Movement->SetBrakeInput(-Val);
	}
}

void ASAFARVehiclePawn::MoveRight(float Val)
{
	UChaosWheeledVehicleMovementComponent* Movement = Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	if (Movement)
	{
		Movement->SetSteeringInput(Val);
	}
}

void ASAFARVehiclePawn::HandbrakePressed()
{
	UChaosWheeledVehicleMovementComponent* Movement = Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	if (Movement && (!SAFARControl || !SAFARControl->bOverrideActive))
	{
		Movement->SetHandbrakeInput(true);
	}
}

void ASAFARVehiclePawn::HandbrakeReleased()
{
	UChaosWheeledVehicleMovementComponent* Movement = Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	if (Movement && (!SAFARControl || !SAFARControl->bOverrideActive))
	{
		Movement->SetHandbrakeInput(false);
	}
}
