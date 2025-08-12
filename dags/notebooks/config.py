"""
Configuration file for data preprocessing
"""

# File paths
DATA_ROOT = "/Users/1113864/LocalDocuments/GitHub/map-search-agent/notebooks/dataload/mobile_plan_info_20250730.json"
CURRENT_DIR = "/Users/1113864/LocalDocuments/GitHub/map-search-agent/notebooks/preprocessing"
RESULT_DIR = "/Users/1113864/LocalDocuments/GitHub/map-search-agent/notebooks/preprocessing/preprocessing_result"

# Drop columns configuration
DROP_COLUMNS = [
    'additionalDataUsage.includedDataSeparateSetting.dataRange',
    'autoProductChange',
    'campaignRelation.signupConcurrentSignup.campaignInformationDTO.campaignList',
    'campaignRelation.signupConcurrentTermination.campaignInformationDTO.campaignList',
    'campaignRelation.signupPreTermination.campaignInformationDTO.campaignList',
    'campaignRelation.terminationConcurrentTermination.campaignInformationDTO.campaignList',
    'campaignRelation.terminationPreTermination.campaignInformationDTO.campaignList',
    'commonRule.lineSuspensionCondition.value',
    'customerInfo.onboardingCustomer.businessCustomerSubtypeRule.eligibility',
    'customerInfo.onboardingCustomer.businessCustomerSubtypeRule.valueList',
    'managementInfo.approvalInfo.value',
    'managementInfo.productOperationPeriod.value',
    'managementInfo.productRequiredNotice.value',
    'managementInfo.productSubscriptionMethod.value',
    'managementInfo.versionInfo.value',
    'otherOnboardInfo.duplicateNameOnboard.domain.valueList',
    'otherOnboardInfo.productChangeLineup.availability.value',
    'processInfo.onboardingDevice.deviceType.eligibility',
    'processInfo.onboardingDevice.deviceType.valueList',
    'processInfo.onboardingServiceCode.eligibility',
    'processInfo.onboardingServiceCode.valueList',
    'productRelation.subRule.productInformation.groupList',
    'productRelation.subRule.productInformation.productList',
    'providingKind.nonDiyVsDiy.value',
    # 0730 기준 새롭게 추가된 제외할 필드
    'billingInfo.billingItem.valueList',
    'billingInfo.billingItemOnInvoice.valueList',
    'customerInfo.onboardingCustomer.welfareBenefitRule',
    'processInfo.devicePurchase',
    'processInfo.subscriptionModificationType',
    'salesInfo.revenueItem.valueList',
    'optionDataChange.changeRule.dateBase.value',
    'optionDataChange.changeRule.date.value'
]

# Table column mappings
TABLE_COLUMNS = {
    'PRODUCT': {
        'source_cols': [
            'pmProductID', 'managementInfo.mappedProductCode.productCode.valueList',
            'managementInfo.generation.valueList', 'managementInfo.marketingKeyword.valueList',
            'managementInfo.productName.value', 'managementInfo.productNameInEnglish.value',
            'managementInfo.lineup.value', 'managementInfo.lineupExt.value',
            'managementInfo.classifiedGroup.value', 'managementInfo.productDescription.value',
            'managementInfo.productSubscriptionCondition.value', 'managementInfo.statusOfOperation.value'
        ],
        'target_cols': [
            'pmProductID', 'mappedProductCode', 'generation', 'marketingKeyword',
            'productName', 'productNameInEnglish', 'lineup', 'lineupExt',
            'classifiedGroup', 'productDescription', 'productSubscriptionCondition', 'statusOfOperation'
        ]
    },
    'PRICE': {
        'source_cols': [
            'pmProductID', 'monthlyPrice.monthlyPrice.value', 'monthlyPrice.monthlyPriceWithoutVAT.value',
            'monthlyPrice.monthlyPriceWithSelectableInstallment.value', 'monthlyPrice.billingMethod.value',
            'salesInfo.netPrice.value'
        ],
        'target_cols': [
            'pmProductID', 'monthlyPrice', 'monthlyPriceWithoutVAT', 'monthlyPriceWithSelectableInstallment',
            'billingMethod', 'netPrice'
        ]
    },
    'VOICE': {
        'source_cols': [
            'pmProductID', 'voice.includedVoiceCall.value', 'voice.includedVideoOrValueAddedCall.value',
            'voice.includedVoiceCallTospecifiedNumbers.voiceCallRange.numberOfService',
            'benefitOfVoiceCall.performRefill.voiceCallRefillRange.refillAmount',
            'benefitOfVoiceCall.performRefill.voiceCallRefillRange.range'
        ],
        'target_cols': [
            'pmProductID', 'includedVoiceCall', 'includedVideoOrValueAddedCall',
            'includedVoiceCallTospecifiedNumbers', 'refillAmount', 'refillRange'
        ]
    },
    'SMS': {
        'source_cols': [
            'pmProductID', 'smsText.includedText.value', 'smsText.includedTextSeparateSetting.textRange'
        ],
        'target_cols': ['pmProductID', 'includedText', 'textRange']
    },
    'DATA': {
        'source_cols': [
            'pmProductID', 'includedData.value', 'additionalDataUsage.includedDataForSharingAndTethering.value',
            'additionalDataUsage.includedMVoIP.value', 'dataQoS.appliedSpeed.value',
            'seniorDataExceedLimit.availableToApply.value', 'generalDataExceedLimit.availableToApply.value',
            'benefitOfData.dataOptionRefill.dataRefillAmount.value',
            'benefitOfData.dataOptionRefill.dataRefillCouponGiftingAvailability.value',
            'benefitOfData.dataOptionGift.maximumShareAmount.value',
            'benefitOfData.dataOptionGiftReceiving.dataGiftReceivingAvailability.value'
        ],
        'target_cols': [
            'pmProductID', 'includedData', 'includedDataForSharingAndTethering', 'includedMVoIP',
            'appliedSpeed', 'seniorDataExceedAvailable', 'generalDataExceedAvailable', 'dataRefillAmount',
            'dataRefillCouponGiftingAvailability', 'maximumShareAmount', 'dataGiftReceivingAvailability'
        ]
    },
    'TOPUP': {
        'source_cols': [
            'pmProductID', 'topupInfo.reChargeAvailability.availability.value',
            'topupInfo.chargeAmount.minimumChargeAmount.value',
            'topupInfo.chargeAmount.maximumChargeAmount.value'
        ],
        'target_cols': ['pmProductID', 'reChargeAvailability', 'minimumChargeAmount', 'maximumChargeAmount']
    },
    'CUSTOMERCONDITION': {
        'source_cols': [
            'pmProductID', 'customerInfo.onboardingCustomer.ageRule',
            'customerInfo.onboardingCustomer.customerTypeRule.eligibility',
            'customerInfo.onboardingCustomer.customerTypeRule.valueList',
            'customerInfo.onboardingCustomer.individualCustomerSubtypeRule.eligibility',
            'customerInfo.onboardingCustomer.individualCustomerSubtypeRule.valueList',
            'otherOnboardInfo.directPlanOnboard.value',
            'otherOnboardInfo.fixedPlanContractConcurrentSignupRestriction.value',
            'otherOnboardInfo.tsupportFundOnboard.value',
            'otherOnboardInfo.duplicateNameOnboard.productGroup.eligibility',
            'otherOnboardInfo.duplicateNameOnboard.productGroup.groupList',
            'otherOnboardInfo.specialCustomerOnboard.isSoldier.value'
        ],
        'target_cols': [
            'pmProductID', 'ageRule', 'customerTypeEligibility', 'customerTypeValueList',
            'individualCustomerSubtypeEligibility', 'individualCustomerSubtypeValueList',
            'directPlanOnboard', 'fixedPlanContractConcurrentSignupRestriction', 'tsupportFundOnboard',
            'duplicateNameOnboardEligibility', 'duplicateNameOnboardGroupList', 'specialCustomerIsSoldier'
        ]
    },
    'BENEFITCONDITION': {
        'source_cols': [
            'pmProductID', 'productBenefitConditions.optionalOfferBenefits.selectableBenefitCount.value',
            'productBenefitConditions.optionalOfferBenefits.selectableBenefitCountPeriodFrom.value',
            'productBenefitConditions.optionalOfferBenefits.selectableBenefitCountPeriodTo.value',
            'productBenefitConditions.optionalOfferBenefits.isAutoEnrollmentBenefitOnSignup.value'
        ],
        'target_cols': [
            'pmProductID', 'selectableBenefitCount', 'selectableBenefitCountPeriodFrom',
            'selectableBenefitCountPeriodTo', 'isAutoEnrollmentBenefitOnSignup'
        ]
    },
    'DEDUCTIBLE': {
        'source_cols': [
            'pmProductID', 'deductibleInfo.deductibilityForDisability.value',
            'deductibleInfo.additionalOfferForDisabilities.value'
        ],
        'target_cols': ['pmProductID', 'deductibilityForDisability', 'additionalOfferForDisabilities']
    }
}

# Field extraction configurations
FIELD_EXTRACTIONS = {
    'benefitOfVoiceCall.performRefill.voiceCallRefillRange': [
        'refillAmount', 'range'
    ],
    'voice.includedVoiceCallVideoOrValueAddedCallSeparateSetting.voiceCallRange': [
        'providingAmount', 'range'
    ],
    'voice.includedVoiceCallTospecifiedNumbers.voiceCallRange': [
        'providingAmount', 'range', 'numberOfService'
    ]
}

# Relation field configurations
RELATION_CONFIGS = {
    'productBenefitConditions.allBenefitList': 'productBenefitConditions.allBenefitList',
    'optionData.dataOptionProvidingMethod': 'optionData.dataOptionProvidingMethod',
    'productRelation.signupConcurrentTermination.productList': 'productRelation.signupConcurrentTermination.productList',
    'productRelation.signupPreTermination.productList': 'productRelation.signupPreTermination.productList',
    'productRelation.terminationConcurrentTermination.productList': 'productRelation.terminationConcurrentTermination.productList',
    'productRelation.terminationPreTermination.productList': 'productRelation.terminationPreTermination.productList'
}

# Additional columns to exclude from target lists
RELATION_EXCLUDE_FIELDS = [
    'optionData.dataOptionProvidingMethod',
    'otherOnboardInfo.duplicateNameOnboard.productGroup.productInformation.groupList',
    'productBenefitConditions.allOfferBenefits.benefitInfo',
    'productBenefitConditions.optionalOfferBenefits.autoSelectedBenefit.productInformation.productList',
    'productBenefitConditions.optionalOfferBenefits.mutuallyExclusiveBenefits',
    'productBenefitConditions.optionalOfferBenefits.optionalOfferBenefitDetailList',
    'productRelation.signupConcurrentTermination.productInformation.groupList',
    'productRelation.signupConcurrentTermination.productInformation.productList',
    'productRelation.signupPreTermination.productInformation.groupList',
    'productRelation.signupPreTermination.productInformation.productList',
    'productRelation.terminationConcurrentTermination.productInformation.groupList',
    'productRelation.terminationConcurrentTermination.productInformation.productList',
    'productRelation.terminationPreTermination.productInformation.productList',
    'productBenefitConditions.allBenefitList'
]

OPTION_DATA_FIELDS = [
    'optionData.optionDataName.value',
    'optionData.selectionMethod.value',
    'optionData.totalNumOfOptions.value',
    'optionData.minNumOfOptionSelectable.value',
    'optionData.maxNumOfOptionSelectable.value'
]