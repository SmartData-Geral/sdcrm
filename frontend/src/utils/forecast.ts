const TEMPERATURE_MULTIPLIERS: Record<string, number> = {
  quente: 0.75,
  morno: 0.5,
  frio: 0.25,
};

export const getForecastTemperatureMultiplier = (temperatura: string | null | undefined): number => {
  const key = (temperatura ?? "").trim().toLowerCase();
  return TEMPERATURE_MULTIPLIERS[key] ?? 0;
};

export const getForecastLeadScoreMultiplier = (leadScore: number | null | undefined): number => {
  if (leadScore == null) return 0;
  const normalizedScore = Math.max(0, Math.min(leadScore, 10));
  return normalizedScore / 10;
};

export const calculateForecastValue = (
  valor: number | null | undefined,
  temperatura: string | null | undefined,
  leadScore: number | null | undefined
): number => {
  if (valor == null || valor <= 0) return 0;
  return valor * getForecastTemperatureMultiplier(temperatura) * getForecastLeadScoreMultiplier(leadScore);
};
