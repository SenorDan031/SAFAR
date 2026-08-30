#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SAFARCommunicationComponent.generated.h"

/**
 * SAFARCommunicationComponent
 * Manages low-latency UDP/TCP communication between Unreal Engine, Python, and C++ SAFAR Core.
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class USAFARCommunicationComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	USAFARCommunicationComponent();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Ports")
	int32 PerceptionPort = 9001;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR Ports")
	int32 ControlPort = 9003;

	UPROPERTY(BlueprintReadOnly, Category = "SAFAR Status")
	bool bConnectedToCore = false;
};
