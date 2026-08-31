#include "SAFARGameModeBase.h"
#include "SAFARVehiclePawn.h"
#include "SAFARHUD.h"

ASAFARGameModeBase::ASAFARGameModeBase()
{
	DefaultPawnClass = ASAFARVehiclePawn::StaticClass();
	HUDClass = ASAFARHUD::StaticClass();
}
