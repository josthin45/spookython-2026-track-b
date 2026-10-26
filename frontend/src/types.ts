export type Curves = {
  S: number[];
  E: number[];
  I: number[];
  R: number[];
};

export type StrategyBlock = {
  incidencia_media: number;
  incidencia_p05: number;
  incidencia_p95: number;
  pico_medio: number;
  ataque_medio: number;
  curvas: Curves;
  zombies_p05: number[];
  zombies_p95: number[];
};

export type Scenario = {
  huella: string;
  recomendacion: string;
  dias: number[];
  params: FormState;
  red: {
    poblacion: number;
    aristas: number;
    hogares: number;
    estudiantes: number;
    comerciantes: number;
    aulas: number;
    buses: number;
    mercados: number;
    grado_medio: number;
    barrios: Record<string, number>;
    nota: string;
  };
  estrategias: {
    estrategia: StrategyBlock;
    azar: StrategyBlock;
    nada: StrategyBlock;
  };
  comparacion: {
    salvados_vs_nada_media: number;
    salvados_vs_nada_p05: number;
    salvados_vs_nada_p95: number;
    reduccion_vs_nada: number;
    salvados_vs_azar_media: number;
    salvados_vs_azar_p05: number;
    salvados_vs_azar_p95: number;
    corridas_mejor_que_nada: number;
    corridas_mejor_que_azar: number;
    corridas: number;
  };
  muestra_prioridad: Array<{
    id: number;
    barrio: string;
    rol: string;
    hogar: number;
    mercado: string;
    colegio: string | null;
    bus: string | null;
    grado: number;
  }>;
  leyenda: {
    estrategia: string;
    azar: string;
    nada: string;
  };
};

export type FormState = {
  seed: number;
  population: number;
  days: number;
  beta: number;
  sigma: number;
  gamma: number;
  vaccines: number;
  vaccine_efficacy: number;
  patient_zero: string;
  locus: string;
  n_runs: number;
  criterio: string;
  intervention: string;
};

export const DEFAULTS: FormState = {
  seed: 42,
  population: 480,
  days: 40,
  beta: 0.16,
  sigma: 0.5,
  gamma: 0.25,
  vaccines: 40,
  vaccine_efficacy: 1,
  patient_zero: "aleatorio",
  locus: "cualquiera",
  n_runs: 8,
  criterio: "anillo",
  intervention: "vacuna",
};
