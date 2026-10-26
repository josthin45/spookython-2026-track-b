import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Chart } from "./Chart";
import { DEFAULTS, type FormState, type Scenario } from "./types";

const STRATEGY = "#0f6e56";
const RANDOM = "#b7791f";
const NONE = "#9d2c2c";

export function App() {
  const [form, setForm] = useState<FormState>(DEFAULTS);
  const [result, setResult] = useState<Scenario | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(next: FormState) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const payload = (await response.json()) as Scenario & { detail?: string; error?: string };
      if (!response.ok) {
        throw new Error(payload.detail || payload.error || "No se pudo simular.");
      }
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Sin conexión con el motor.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void run(DEFAULTS);
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(form);
  }

  function surprise(kind: "doble" | "mitad" | "mercado" | "eficacia") {
    const next = { ...form };
    if (kind === "doble") next.beta = round(Math.min(1, form.beta * 2), 2);
    if (kind === "mitad") next.vaccines = Math.max(0, Math.floor(form.vaccines / 2));
    if (kind === "mercado") next.locus = "mercado";
    if (kind === "eficacia") next.vaccine_efficacy = 0.6;
    setForm(next);
    void run(next);
  }

  const saved = result?.comparacion.salvados_vs_nada_media ?? 0;

  return (
    <main className="app">
      <header>
        <p className="kicker">Spookython 2026 · Track B · Manta</p>
        <h1>Comité de Contención</h1>
        <p>
          Gripe Z se mueve por hogares, aulas, buses y mercados. Hay pocas dosis. Esta mesa compara
          vacunar por centralidad contra no hacer nada y contra gastar las mismas dosis al azar.
        </p>
      </header>

      <div className="layout">
        <form className="panel" onSubmit={submit}>
          <h2>Escenario</h2>
          <Field label="Semilla" hint="La misma semilla repite el resultado exacto.">
            <input
              type="number"
              min={0}
              value={form.seed}
              onChange={(event) => update("seed", Number(event.target.value))}
            />
          </Field>
          <Field label="Personas en la muestra" hint="No es el cantón entero. Manta tiene 271.145 habitantes.">
            <input
              type="number"
              min={80}
              max={1200}
              value={form.population}
              onChange={(event) => update("population", Number(event.target.value))}
            />
          </Field>
          <Field label="Días">
            <input
              type="number"
              min={7}
              max={90}
              value={form.days}
              onChange={(event) => update("days", Number(event.target.value))}
            />
          </Field>
          <Field label="Contagio β" hint="Probabilidad diaria en un contacto de hogar.">
            <div className="row">
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={form.beta}
                onChange={(event) => update("beta", Number(event.target.value))}
              />
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={form.beta}
                onChange={(event) => update("beta", Number(event.target.value))}
              />
            </div>
          </Field>
          <Field label="Incubación σ" hint="0,50 ≈ 2 días de mordido a zombie.">
            <input
              type="number"
              min={0.01}
              max={1}
              step={0.01}
              value={form.sigma}
              onChange={(event) => update("sigma", Number(event.target.value))}
            />
          </Field>
          <Field label="Recuperación γ" hint="0,25 ≈ 4 días infeccioso.">
            <input
              type="number"
              min={0.01}
              max={1}
              step={0.01}
              value={form.gamma}
              onChange={(event) => update("gamma", Number(event.target.value))}
            />
          </Field>
          <Field label="Presupuesto K" hint="Dosis o aislamientos. Solo sobre personas sanas.">
            <input
              type="number"
              min={0}
              value={form.vaccines}
              onChange={(event) => update("vaccines", Number(event.target.value))}
            />
          </Field>
          <Field label="Eficacia de la vacuna" hint="1 protege del todo. 0,6 es la eficacia parcial del brote sorpresa.">
            <div className="row">
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={form.vaccine_efficacy}
                onChange={(event) => update("vaccine_efficacy", Number(event.target.value))}
              />
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={form.vaccine_efficacy}
                onChange={(event) => update("vaccine_efficacy", Number(event.target.value))}
              />
            </div>
          </Field>
          <Field label="Dónde empieza">
            <select value={form.locus} onChange={(event) => update("locus", event.target.value)}>
              <option value="cualquiera">Cualquier persona</option>
              <option value="hogar">Un hogar</option>
              <option value="colegio">Un colegio</option>
              <option value="bus">Un bus</option>
              <option value="mercado">Un mercado</option>
            </select>
          </Field>
          <Field label="Paciente cero" hint="'aleatorio' o el id de una persona.">
            <input
              value={form.patient_zero}
              onChange={(event) => update("patient_zero", event.target.value)}
            />
          </Field>
          <Field label="Corridas Monte Carlo" hint="Se reporta la media y el rango p5–p95.">
            <input
              type="number"
              min={1}
              max={30}
              value={form.n_runs}
              onChange={(event) => update("n_runs", Number(event.target.value))}
            />
          </Field>
          <Field
            label="A quién proteger"
            hint="Anillo: hogar y contactos del caso, y con lo que sobre, la gente de mayor grado."
          >
            <select value={form.criterio} onChange={(event) => update("criterio", event.target.value)}>
              <option value="anillo">Anillo del caso y luego grado</option>
              <option value="degree">Solo mayor grado</option>
              <option value="puentes">Puentes entre grupos</option>
              <option value="betweenness">Intermediación</option>
            </select>
          </Field>
          <Field label="Intervención">
            <select
              value={form.intervention}
              onChange={(event) => update("intervention", event.target.value)}
            >
              <option value="vacuna">Vacunar</option>
              <option value="cuarentena">Cuarentena de sitios públicos</option>
            </select>
          </Field>
          <div className="actions">
            <button className="primary" type="submit" disabled={loading}>
              {loading ? "Simulando…" : "Simular brote"}
            </button>
            <button
              className="ghost"
              type="button"
              onClick={() => {
                setForm(DEFAULTS);
                void run(DEFAULTS);
              }}
            >
              Restaurar
            </button>
          </div>
        </form>

        <section>
          <div className="presets" aria-label="Brote sorpresa">
            <button type="button" onClick={() => surprise("doble")}>
              Doble contagio
            </button>
            <button type="button" onClick={() => surprise("mitad")}>
              Mitad de dosis
            </button>
            <button type="button" onClick={() => surprise("mercado")}>
              Brote en el mercado
            </button>
            <button type="button" onClick={() => surprise("eficacia")}>
              Eficacia 60%
            </button>
          </div>

          {error ? <p className="error">{error}</p> : null}

          {result ? (
            <>
              <div className={saved > 0 ? "banner" : "banner warn"}>
                <strong>{saved > 0 ? "Recomendación" : "No recomendar este plan"}</strong>
                <p>{result.recomendacion}</p>
              </div>
              <div className="cards">
                <article className="card">
                  <span>Salvadas frente a no intervenir</span>
                  <strong>{people(result.comparacion.salvados_vs_nada_media)}</strong>
                  <span>
                    p5–p95 {people(result.comparacion.salvados_vs_nada_p05)} a{" "}
                    {people(result.comparacion.salvados_vs_nada_p95)} ·{" "}
                    {percent(result.comparacion.reduccion_vs_nada)} menos contagios
                  </span>
                </article>
                <article className="card">
                  <span>Salvadas frente al azar</span>
                  <strong>{people(result.comparacion.salvados_vs_azar_media)}</strong>
                  <span>
                    p5–p95 {people(result.comparacion.salvados_vs_azar_p05)} a{" "}
                    {people(result.comparacion.salvados_vs_azar_p95)} · gana en{" "}
                    {result.comparacion.corridas_mejor_que_azar}/{result.comparacion.corridas} corridas
                  </span>
                </article>
                <article className="card">
                  <span>Contagios con la estrategia</span>
                  <strong>{people(result.estrategias.estrategia.incidencia_media)}</strong>
                  <span>
                    de {result.red.poblacion} ({percent(result.estrategias.estrategia.ataque_medio)}). Sin plan{" "}
                    {people(result.estrategias.nada.incidencia_media)} · al azar{" "}
                    {people(result.estrategias.azar.incidencia_media)}
                  </span>
                </article>
              </div>

              <Chart
                title="Zombies por día, media de las corridas"
                days={result.dias}
                band={{
                  low: result.estrategias.estrategia.zombies_p05,
                  high: result.estrategias.estrategia.zombies_p95,
                  color: STRATEGY,
                }}
                series={[
                  { name: result.leyenda.estrategia, color: STRATEGY, values: result.estrategias.estrategia.curvas.I },
                  { name: result.leyenda.azar, color: RANDOM, values: result.estrategias.azar.curvas.I },
                  { name: result.leyenda.nada, color: NONE, values: result.estrategias.nada.curvas.I },
                ]}
              />
              <Chart
                title="Estados con la estrategia"
                days={result.dias}
                series={[
                  { name: "Sano", color: "#4d7c0f", values: result.estrategias.estrategia.curvas.S },
                  { name: "Mordido", color: "#b7791f", values: result.estrategias.estrategia.curvas.E },
                  { name: "Zombie", color: "#9d2c2c", values: result.estrategias.estrategia.curvas.I },
                  { name: "Exorcizado", color: "#1d4e89", values: result.estrategias.estrategia.curvas.R },
                ]}
              />

              <article className="panel">
                <h2>A quién cubrir primero</h2>
                <p className="meta">
                  Primeras personas del ranking en la corrida 1. No incluye al paciente cero: ya está
                  infectado. Con eficacia total, el día 0 esas personas pasan a inmunes y por eso la
                  curva azul no arranca en cero.
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Id</th>
                      <th>Rol</th>
                      <th>Barrio</th>
                      <th>Hogar</th>
                      <th>Dónde mezcla</th>
                      <th>Grado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.muestra_prioridad.map((person) => (
                      <tr key={person.id}>
                        <td>{person.id}</td>
                        <td>{person.rol}</td>
                        <td>{person.barrio}</td>
                        <td>{person.hogar}</td>
                        <td>{person.colegio || person.bus || person.mercado}</td>
                        <td>{person.grado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>

              <p className="meta foot">
                Huella {result.huella} · semilla {result.params.seed} · {result.red.poblacion} personas ·{" "}
                {result.red.hogares} hogares · {result.red.aulas} aulas · {result.red.buses} buses ·{" "}
                {result.red.comerciantes} comerciantes · grado medio {result.red.grado_medio}. {result.red.nota}
              </p>
            </>
          ) : loading ? (
            <p>Calculando el brote…</p>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

function people(value: number) {
  return new Intl.NumberFormat("es-EC", { maximumFractionDigits: 0 }).format(value);
}

function percent(value: number) {
  const digits = value > 0 && value < 0.01 ? 1 : 0;
  return new Intl.NumberFormat("es-EC", {
    style: "percent",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function round(value: number, digits: number) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}
