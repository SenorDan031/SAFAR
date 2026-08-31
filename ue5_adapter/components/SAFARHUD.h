#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "SAFARHUD.generated.h"

/**
 * ASAFARHUD
 * Renders on-screen real-time ADAS telemetry and threat indicators directly in the UE5 viewport.
 */
UCLASS()
class ASAFARHUD : public AHUD
{
	GENERATED_BODY()

public:
	ASAFARHUD();

	virtual void DrawHUD() override;

protected:
	void DrawSAFAROverlay();
};
