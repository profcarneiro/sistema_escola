import React, { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Users, Calendar, Filter, CheckCircle, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';

const fmtBRL = (val) => `R$ ${Number(val || 0).toFixed(2).replace('.', ',')}`;

const MESES_CURTOS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

const fmtYM = (ym) => {
  if (!ym || !ym.includes('-')) return ym;
  const [y, m] = ym.split('-');
  const idx = parseInt(m, 10) - 1;
  return `${MESES_CURTOS[idx] || m}/${y.slice(2)}`;
};

export function MonthlyCashFlowSection({ showToast }) {
  const [ano, setAno] = useState(String(new Date().getFullYear()));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.getMonthlyCashFlow(ano);
      setData(res);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [ano]);

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-wrap justify-between items-center gap-3">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Fluxo de Caixa Mês a Mês (Regime de Caixa)</h3>
          <p className="text-xs text-slate-500">Mensalidades efetivamente recebidas menos pagamentos de professores, comercial e cada categoria de despesa na data do pagamento.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-slate-600">Ano:</label>
          <input
            type="number"
            value={ano}
            onChange={(e) => setAno(e.target.value)}
            className="w-24 px-3 py-1.5 border rounded-lg text-xs"
          />
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-emerald-800 uppercase block">Entradas no Ano</span>
            <span className="text-lg font-bold text-emerald-900">{fmtBRL(data.total_entradas_ano)}</span>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-500 uppercase block">Pgto. Professores</span>
            <span className="text-lg font-bold text-red-700">-{fmtBRL(data.total_professores_ano)}</span>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-500 uppercase block">Pgto. Comercial</span>
            <span className="text-lg font-bold text-red-700">-{fmtBRL(data.total_comercial_ano)}</span>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-500 uppercase block">Demais Despesas</span>
            <span className="text-lg font-bold text-red-700">-{fmtBRL(data.total_despesas_ano)}</span>
          </div>
          <div className={`border p-4 rounded-xl ${data.resultado_caixa_ano >= 0 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
            <span className="text-[11px] font-semibold text-slate-700 uppercase block">Resultado Caixa Ano</span>
            <span className={`text-lg font-bold ${data.resultado_caixa_ano >= 0 ? 'text-amber-900' : 'text-red-800'}`}>
              {fmtBRL(data.resultado_caixa_ano)}
            </span>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-600">
          <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 border-b">
            <tr>
              <th className="px-3 py-3 whitespace-nowrap">Mês</th>
              <th className="px-3 py-3 text-right whitespace-nowrap text-emerald-700">Mensalidades</th>
              <th className="px-3 py-3 text-right whitespace-nowrap text-emerald-700">Workshops</th>
              <th className="px-3 py-3 text-right whitespace-nowrap">Professores</th>
              <th className="px-3 py-3 text-right whitespace-nowrap">Comercial</th>
              {(data?.categorias_despesas || []).map((cat) => (
                <th key={cat} className="px-3 py-3 text-right whitespace-nowrap">{cat}</th>
              ))}
              <th className="px-3 py-3 text-right whitespace-nowrap">Total Saídas</th>
              <th className="px-3 py-3 text-right whitespace-nowrap">Saldo Mês</th>
              <th className="px-3 py-3 text-right whitespace-nowrap">Saldo Acum.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-400">Calculando fluxo de caixa...</td></tr>
            ) : (data?.meses || []).map((m) => (
              <tr key={m.competencia} className="hover:bg-slate-50">
                <td className="px-3 py-2.5 font-bold text-slate-800 whitespace-nowrap">{fmtYM(m.competencia)}</td>
                <td className="px-3 py-2.5 text-right text-emerald-700 font-semibold whitespace-nowrap">{fmtBRL(m.mensalidades_recebidas)}</td>
                <td className="px-3 py-2.5 text-right text-emerald-700 whitespace-nowrap">{fmtBRL(m.receitas_workshops)}</td>
                <td className="px-3 py-2.5 text-right text-red-700 whitespace-nowrap">{fmtBRL(m.pagamentos_professores)}</td>
                <td className="px-3 py-2.5 text-right text-red-700 whitespace-nowrap">{fmtBRL(m.pagamento_comercial)}</td>
                {(data?.categorias_despesas || []).map((cat) => (
                  <td key={cat} className="px-3 py-2.5 text-right whitespace-nowrap">{fmtBRL(m.despesas_por_categoria?.[cat] || 0)}</td>
                ))}
                <td className="px-3 py-2.5 text-right font-semibold text-red-700 whitespace-nowrap">{fmtBRL(m.total_saidas)}</td>
                <td className={`px-3 py-2.5 text-right font-bold whitespace-nowrap ${m.saldo_mes >= 0 ? 'text-emerald-800' : 'text-red-700'}`}>
                  {fmtBRL(m.saldo_mes)}
                </td>
                <td className={`px-3 py-2.5 text-right font-bold whitespace-nowrap ${m.saldo_acumulado >= 0 ? 'text-slate-800' : 'text-red-700'}`}>
                  {fmtBRL(m.saldo_acumulado)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Forecast12MonthsSection({ showToast }) {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [assumptions, setAssumptions] = useState({
    novos_alunos_mes: '2',
    saidas_alunos_mes: '0',
    custo_fixo_mensal_estimado: '0',
    ticket_medio_override: '0',
  });

  const fetchForecast = async (custom = null) => {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      const src = custom || assumptions;
      if (src.novos_alunos_mes !== '') p.set('novos_alunos_mes', src.novos_alunos_mes);
      if (src.saidas_alunos_mes !== '') p.set('saidas_alunos_mes', src.saidas_alunos_mes);
      if (src.custo_fixo_mensal_estimado !== '') p.set('custo_fixo_mensal_estimado', src.custo_fixo_mensal_estimado);
      if (src.ticket_medio_override !== '') p.set('ticket_medio_override', src.ticket_medio_override);
      const res = await api.getForecast12Months(custom ? p.toString() : '');
      setForecast(res);
      if (!custom && res?.premissas) {
        setAssumptions({
          novos_alunos_mes: String(res.premissas.novos_alunos_mes),
          saidas_alunos_mes: String(res.premissas.saidas_alunos_mes),
          custo_fixo_mensal_estimado: String(res.premissas.custo_fixo_mensal_estimado),
          ticket_medio_override: String(res.premissas.ticket_medio_override),
        });
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
  }, []);

  const handleSaveAssumptions = async (e) => {
    e.preventDefault();
    try {
      await api.updateForecastSettings({
        novos_alunos_mes: parseInt(assumptions.novos_alunos_mes || 0, 10),
        saidas_alunos_mes: parseInt(assumptions.saidas_alunos_mes || 0, 10),
        custo_fixo_mensal_estimado: parseFloat(assumptions.custo_fixo_mensal_estimado || 0),
        ticket_medio_override: parseFloat(assumptions.ticket_medio_override || 0),
      });
      showToast('Premissas salvas e previsão recalculada!');
      fetchForecast(assumptions);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Previsão Financeira — Próximos 12 Meses</h3>
          <p className="text-xs text-slate-500">
            Projeção de matrículas, receita contratada + expansão, ponto de equilíbrio em nº de alunos, divisão de lucro Dani/Helena (50%) e comparativo previsto x realizado.
          </p>
        </div>

        <form onSubmit={handleSaveAssumptions} className="grid grid-cols-2 lg:grid-cols-5 gap-3 bg-slate-50 p-3.5 rounded-xl border text-xs items-end">
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Novos alunos / mês</label>
            <input type="number" min="0" value={assumptions.novos_alunos_mes} onChange={e => setAssumptions({ ...assumptions, novos_alunos_mes: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Saídas extras / mês</label>
            <input type="number" min="0" value={assumptions.saidas_alunos_mes} onChange={e => setAssumptions({ ...assumptions, saidas_alunos_mes: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Custo Fixo Base (R$/mês)</label>
            <input type="number" step="0.01" min="0" value={assumptions.custo_fixo_mensal_estimado} onChange={e => setAssumptions({ ...assumptions, custo_fixo_mensal_estimado: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Ticket Médio Manual (0=auto)</label>
            <input type="number" step="0.01" min="0" value={assumptions.ticket_medio_override} onChange={e => setAssumptions({ ...assumptions, ticket_medio_override: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => fetchForecast(assumptions)} className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg font-semibold">Simular</button>
            <button type="submit" className="px-3 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-semibold flex-1">Salvar Padrão</button>
          </div>
        </form>
      </div>

      {forecast && (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-[11px] text-slate-500 uppercase font-semibold block">Ticket Ref. ({forecast.alunos_ativos_atual} ativos)</span>
            <span className="text-lg font-bold text-slate-800">{fmtBRL(forecast.ticket_medio_referencia)}</span>
          </div>
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-[11px] text-slate-500 uppercase font-semibold block">Receita Prev. 12m</span>
            <span className="text-lg font-bold text-emerald-700">{fmtBRL(forecast.receita_prevista_total)}</span>
          </div>
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-[11px] text-slate-500 uppercase font-semibold block">Saídas Prev. 12m</span>
            <span className="text-lg font-bold text-red-700">{fmtBRL(forecast.saidas_previstas_total)}</span>
          </div>
          <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 shadow-sm">
            <span className="text-[11px] text-amber-800 uppercase font-semibold block">Resultado Prev. 12m</span>
            <span className="text-lg font-bold text-amber-900">{fmtBRL(forecast.resultado_previsto_total)}</span>
          </div>
          <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 shadow-sm">
            <span className="text-[11px] text-emerald-800 uppercase font-semibold block">Dani (50%) / Helena (50%)</span>
            <span className="text-sm font-bold text-emerald-900 block">{fmtBRL(forecast.lucro_dani_total)} cada</span>
          </div>
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-[11px] text-slate-500 uppercase font-semibold block">Realizado Acum.</span>
            <span className="text-lg font-bold text-slate-800">{fmtBRL(forecast.resultado_realizado_total)}</span>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-600">
          <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 border-b">
            <tr>
              <th className="px-3 py-3">Mês</th>
              <th className="px-3 py-3 text-center">Alunos (+Nov/-Saíd)</th>
              <th className="px-3 py-3 text-center">P. Equilíbrio</th>
              <th className="px-3 py-3 text-right">Rec. Prevista</th>
              <th className="px-3 py-3 text-right">Saídas Prev.</th>
              <th className="px-3 py-3 text-right">Res. Previsto</th>
              <th className="px-3 py-3 text-right text-emerald-800">Dani (50%)</th>
              <th className="px-3 py-3 text-right text-emerald-800">Helena (50%)</th>
              <th className="px-3 py-3 text-right">Realizado (Rec-Saíd)</th>
              <th className="px-3 py-3 text-right">Desvio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-slate-400">Calculando previsão...</td></tr>
            ) : (forecast?.meses || []).map((m) => (
              <tr key={m.competencia} className="hover:bg-slate-50">
                <td className="px-3 py-2.5 font-bold text-slate-800 whitespace-nowrap">{fmtYM(m.competencia)}</td>
                <td className="px-3 py-2.5 text-center whitespace-nowrap">
                  <b>{m.alunos_ativos_fim}</b>{' '}
                  <span className="text-[11px] text-slate-400">(+{m.novos_alunos_previstos}/-{m.saidas_previstas})</span>
                </td>
                <td className="px-3 py-2.5 text-center font-semibold text-amber-800">{m.ponto_equilibrio_alunos} al.</td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap">{fmtBRL(m.receita_prevista)}</td>
                <td className="px-3 py-2.5 text-right text-red-700 whitespace-nowrap">{fmtBRL(m.saidas_previstas_valor)}</td>
                <td className={`px-3 py-2.5 text-right font-bold whitespace-nowrap ${m.resultado_previsto >= 0 ? 'text-slate-800' : 'text-red-700'}`}>
                  {fmtBRL(m.resultado_previsto)}
                </td>
                <td className="px-3 py-2.5 text-right text-emerald-700 font-semibold whitespace-nowrap">{fmtBRL(m.lucro_dani)}</td>
                <td className="px-3 py-2.5 text-right text-emerald-700 font-semibold whitespace-nowrap">{fmtBRL(m.lucro_helena)}</td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap">{fmtBRL(m.resultado_realizado)}</td>
                <td className={`px-3 py-2.5 text-right font-semibold whitespace-nowrap ${m.variacao_resultado >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                  {fmtBRL(m.variacao_resultado)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StudentMonthlyMatrixSection({ showToast, classes = [] }) {
  const [ano, setAno] = useState(String(new Date().getFullYear()));
  const [busca, setBusca] = useState('');
  const [turmaId, setTurmaId] = useState('');
  const [apenasAtivos, setApenasAtivos] = useState(true);
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadMatrix = async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (ano) p.set('ano', ano);
      p.set('apenas_ativos', String(apenasAtivos));
      if (busca.trim()) p.set('busca', busca.trim());
      if (turmaId) p.set('turma_id', turmaId);
      const res = await api.getStudentMonthlyMatrix(p.toString());
      setMatrix(res);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMatrix();
  }, [ano, apenasAtivos, turmaId]);

  const cellStyle = (status) => {
    switch (status) {
      case 'PAGO': return 'bg-emerald-100 text-emerald-900 border-emerald-200';
      case 'ATRASADO': return 'bg-red-100 text-red-900 border-red-200';
      case 'PARCIAL': return 'bg-amber-100 text-amber-900 border-amber-200';
      case 'PENDENTE': return 'bg-blue-50 text-blue-800 border-blue-200';
      case 'CORTESIA': return 'bg-purple-50 text-purple-800 border-purple-200';
      default: return 'bg-slate-50 text-slate-400 border-slate-100';
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-wrap justify-between items-center gap-3">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Controle Mensal por Aluno (Grade Matricial)</h3>
          <p className="text-xs text-slate-500">Visão consolidada aluno x meses exibindo status e valor pago em cada competência.</p>
        </div>
        <div className="flex flex-wrap gap-2 items-center text-xs">
          <input type="number" value={ano} onChange={e => setAno(e.target.value)} className="w-20 px-2.5 py-1.5 border rounded-lg" />
          <select value={turmaId} onChange={e => setTurmaId(e.target.value)} className="px-2.5 py-1.5 border rounded-lg bg-white">
            <option value="">Todas as turmas</option>
            {classes.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
          <input
            type="text"
            placeholder="Buscar aluno..."
            value={busca}
            onChange={e => setBusca(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadMatrix()}
            className="px-3 py-1.5 border rounded-lg"
          />
          <label className="flex items-center gap-1.5 cursor-pointer font-semibold text-slate-700">
            <input type="checkbox" checked={apenasAtivos} onChange={e => setApenasAtivos(e.target.checked)} />
            Apenas ativos
          </label>
          <button type="button" onClick={loadMatrix} className="px-3 py-1.5 bg-slate-800 text-white rounded-lg font-semibold">Filtrar</button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-[11px] text-slate-600">
          <thead className="bg-slate-50 uppercase text-slate-500 border-b">
            <tr>
              <th className="px-3 py-3 sticky left-0 bg-slate-50 z-10 min-w-[180px]">Aluno</th>
              {(matrix?.meses || []).map((comp) => (
                <th key={comp} className="px-2 py-3 text-center whitespace-nowrap min-w-[88px]">{fmtYM(comp)}</th>
              ))}
              <th className="px-3 py-3 text-right whitespace-nowrap">Total Pago Ano</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={14} className="px-4 py-8 text-center text-slate-400">Carregando grade mensal...</td></tr>
            ) : (matrix?.alunos || []).length === 0 ? (
              <tr><td colSpan={14} className="px-4 py-8 text-center text-slate-400">Nenhum aluno encontrado.</td></tr>
            ) : matrix.alunos.map((row) => (
              <tr key={row.aluno_id} className="hover:bg-slate-50">
                <td className="px-3 py-2 sticky left-0 bg-white z-10 border-r">
                  <div className="font-bold text-slate-800">{row.aluno_nome}</div>
                  {row.turmas.length > 0 && <div className="text-[10px] text-slate-400 truncate max-w-[170px]">{row.turmas.join(', ')}</div>}
                </td>
                {matrix.meses.map((comp) => {
                  const c = row.celulas?.[comp];
                  if (!c || c.status === 'SEM_COBRANCA') {
                    return <td key={comp} className="px-1.5 py-2 text-center text-slate-300">—</td>;
                  }
                  if (c.status === 'CORTESIA') {
                    return (
                      <td key={comp} className="px-1 py-1.5 text-center">
                        <div className={`px-1.5 py-1 rounded border font-semibold ${cellStyle('CORTESIA')}`}>CORTESIA</div>
                      </td>
                    );
                  }
                  const valExibir = c.valor_pago > 0 ? c.valor_pago : c.valor_previsto;
                  return (
                    <td key={comp} className="px-1 py-1.5 text-center">
                      <div className={`px-1.5 py-1 rounded border ${cellStyle(c.status)}`} title={`Previsto: ${fmtBRL(c.valor_previsto)} | Pago: ${fmtBRL(c.valor_pago)}`}>
                        <div className="font-bold text-[10px]">{c.status}</div>
                        <div className="whitespace-nowrap">{fmtBRL(valExibir)}</div>
                      </div>
                    </td>
                  );
                })}
                <td className="px-3 py-2 text-right font-bold text-emerald-800 whitespace-nowrap">
                  {fmtBRL(row.total_pago_ano)}
                  <div className="text-[10px] font-normal text-slate-400">de {fmtBRL(row.total_previsto_ano)}</div>
                </td>
              </tr>
            ))}
          </tbody>
          {matrix && (
            <tfoot className="bg-slate-50 border-t font-bold text-slate-700">
              <tr>
                <td className="px-3 py-2.5 sticky left-0 bg-slate-50">Totais Recebidos</td>
                {matrix.meses.map((comp) => (
                  <td key={comp} className="px-2 py-2.5 text-center text-emerald-800 whitespace-nowrap">
                    {fmtBRL(matrix.totais_pago_mes?.[comp] || 0)}
                  </td>
                ))}
                <td className="px-3 py-2.5 text-right text-emerald-900 whitespace-nowrap">
                  {fmtBRL(Object.values(matrix.totais_pago_mes || {}).reduce((a, b) => a + b, 0))}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
