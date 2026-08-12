export type AnalyticsData = {
  meta: {
    title: string;
    subtitle: string;
    records: number;
    generatedFrom: string;
  };
  kpis: {
    totalRecords: number;
    failures: number;
    failureRate: number;
    healthyRate: number;
    avgTorque: number;
    avgRpm: number;
    avgToolWear: number;
    avgTempDelta: number;
    medianWearFailures: number;
    highRiskShare: number;
  };
  byProductType: Array<{
    type: string;
    label: string;
    total: number;
    failures: number;
    failureRate: number;
    avgTorque: number;
    avgRpm: number;
    avgWear: number;
    avgAirTemp: number;
    avgProcessTemp: number;
  }>;
  failureTypes: Array<{
    code: string;
    name: string;
    count: number;
    shareOfFailures: number;
  }>;
  riskBands: Array<{
    band: string;
    total: number;
    failures: number;
    failureRate: number;
  }>;
  wearBins: Array<{
    range: string;
    total: number;
    failures: number;
    failureRate: number;
  }>;
  torqueBins: Array<{
    range: string;
    total: number;
    failures: number;
    failureRate: number;
  }>;
  tempDeltaBins: Array<{
    range: string;
    total: number;
    failures: number;
    failureRate: number;
  }>;
  rpmBins: Array<{
    range: string;
    total: number;
    failures: number;
    failureRate: number;
    avgTorque: number;
  }>;
  failureMixByType: Array<Record<string, string | number>>;
  scatter: Array<{
    rpm: number;
    torque: number;
    wear: number;
    failed: boolean;
    type: string;
    failureType: string;
  }>;
  topFailures: Array<{
    udi: number;
    productId: string;
    type: string;
    failureType: string;
    risk: string;
    wear: number;
    torque: number;
    rpm: number;
    tempDelta: number;
  }>;
  insights: string[];
};
