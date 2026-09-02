// Fill out your copyright notice in the Description page of Project Settings.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "UEPotholeScanner.generated.h"

/**
 * UEPotholeScanner
 * Scans the road surface ahead using dynamic ground line-traces to detect depth voids (potholes/craters).
 */
UCLASS(ClassGroup=(SAFAR), meta=(BlueprintSpawnableComponent))
class UEPotholeScanner : public UActorComponent
{
	GENERATED_BODY()

public:
	UEPotholeScanner();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR|Pothole")
	float ScanLookaheadMeters = 30.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAFAR|Pothole")
	float GroundClearanceThresholdMeters = 0.16f;

	UFUNCTION(BlueprintCallable, Category = "SAFAR|Pothole")
	bool DetectPotholeVoid(FVector& OutLocation, float& OutDepthMeters, float& OutWidthMeters);
};
