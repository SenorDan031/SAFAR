#include "SAFARHUD.h"
#include "SAFARControlComponent.h"
#include "SAFARSensorComponent.h"
#include "SAFARCommunicationComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "GameFramework/Pawn.h"

ASAFARHUD::ASAFARHUD()
{
}

void ASAFARHUD::DrawHUD()
{
	Super::DrawHUD();
	DrawSAFAROverlay();
}

void ASAFARHUD::DrawSAFAROverlay()
{
	if (!Canvas)
	{
		return;
	}

	APawn* Pawn = GetOwningPawn();
	if (!Pawn)
	{
		return;
	}

	USAFARControlComponent* ControlComp = Pawn->FindComponentByClass<USAFARControlComponent>();
	USAFARSensorComponent* SensorComp = Pawn->FindComponentByClass<USAFARSensorComponent>();
	USAFARCommunicationComponent* CommComp = Pawn->FindComponentByClass<USAFARCommunicationComponent>();

	float ThreatScore = ControlComp ? ControlComp->ThreatScore : 0.0f;
	bool bOverride = ControlComp ? ControlComp->bOverrideActive : false;
	FString HUDStatus = ControlComp ? ControlComp->CurrentHUDStatus : TEXT("SAFAR: INITIALIZING");
	float SpeedKmh = SensorComp ? SensorComp->VehicleSpeedKmh : 0.0f;
	bool bConnected = CommComp ? CommComp->bConnectedToCore : false;

	const float BoxX = 20.0f;
	const float BoxY = 20.0f;
	const float BoxW = 460.0f;
	const float BoxH = 110.0f;

	FLinearColor BgColor(0.05f, 0.08f, 0.12f, 0.85f);
	FCanvasTileItem BgItem(FVector2D(BoxX, BoxY), FVector2D(BoxW, BoxH), BgColor);
	BgItem.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(BgItem);

	FLinearColor HeaderColor = bOverride ? FLinearColor(1.0f, 0.15f, 0.15f, 1.0f) : FLinearColor(0.2f, 0.9f, 0.4f, 1.0f);
	FString HeaderText = FString::Printf(
		TEXT("SAFAR ADAS | MODE: %s | SPEED: %.0f KM/H"),
		bOverride ? TEXT("AUTONOMOUS BRAKE") : TEXT("PASSIVE DRIVER"),
		SpeedKmh
	);
	Canvas->DrawText(GEngine->GetSmallFont(), HeaderText, BoxX + 15.0f, BoxY + 12.0f, 1.1f, 1.1f, HeaderColor);

	const float BarX = BoxX + 15.0f;
	const float BarY = BoxY + 40.0f;
	const float BarW = 430.0f;
	const float BarH = 16.0f;

	FCanvasTileItem BarBg(FVector2D(BarX, BarY), FVector2D(BarW, BarH), FLinearColor(0.2f, 0.2f, 0.2f, 0.9f));
	Canvas->DrawItem(BarBg);

	float ClampedThreat = FMath::Clamp(ThreatScore, 0.0f, 1.0f);
	FLinearColor FillColor = (ClampedThreat >= 0.70f) ? FLinearColor(1.0f, 0.1f, 0.1f, 1.0f) :
	                         (ClampedThreat >= 0.35f) ? FLinearColor(1.0f, 0.8f, 0.1f, 1.0f) :
	                                                   FLinearColor(0.2f, 0.8f, 0.3f, 1.0f);

	FCanvasTileItem BarFill(FVector2D(BarX, BarY), FVector2D(BarW * ClampedThreat, BarH), FillColor);
	Canvas->DrawItem(BarFill);

	FString ThreatText = FString::Printf(TEXT("Threat Score: %.2f / 1.00"), ThreatScore);
	Canvas->DrawText(GEngine->GetSmallFont(), ThreatText, BarX + 5.0f, BarY + 2.0f, 0.9f, 0.9f, FLinearColor::White);

	FString ActionText = HUDStatus.IsEmpty() ? TEXT("Status: Corridor Clear") : HUDStatus;
	Canvas->DrawText(GEngine->GetSmallFont(), ActionText, BoxX + 15.0f, BoxY + 68.0f, 0.95f, 0.95f, FLinearColor(0.85f, 0.9f, 1.0f, 1.0f));

	FString ConnText = FString::Printf(
		TEXT("Core Link (UDP 9003): %s | Perception (TCP 9001): %s"),
		bConnected ? TEXT("ACTIVE") : TEXT("SEARCHING..."),
		(CommComp && CommComp->bConnectedToPerception) ? TEXT("STREAMING") : TEXT("CONNECTING...")
	);
	Canvas->DrawText(GEngine->GetSmallFont(), ConnText, BoxX + 15.0f, BoxY + 88.0f, 0.8f, 0.8f, FLinearColor(0.6f, 0.7f, 0.8f, 1.0f));
}
