#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "SAFARGameModeBase.generated.h"

/**
 * ASAFARGameModeBase
 * Default Game Mode configuring ASAFARVehiclePawn as Default Pawn and ASAFARHUD as Default HUD.
 */
UCLASS()
class ASAFARGameModeBase : public AGameModeBase
{
	GENERATED_BODY()

public:
	ASAFARGameModeBase();
};
