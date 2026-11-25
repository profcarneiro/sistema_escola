import React, { useState, useEffect } from 'react';
import {
  Plus, Download, Edit, Trash2, CheckCircle, AlertTriangle,
  DollarSign, Users, Briefcase, Palette, BarChart2, X, Check, Filter, ChevronDown
} from 'lucide-react';
import { api } from '../services/api';

const CATEGORIAS_DESPESA = [
  'Aluguel',
  'Água',
  'Luz',
  'Internet/Telefone',
  'Material',
  'Contador',
  'Impostos',
  'Marketing',
  'Manutenção',
  'Limpeza',
  'Pagamento Professor',
  'Comissão Comercial',
  'Repasse Parceria',
  'Outros',
];

const MESES_OPTS = [
  { id: '1', label: 'Janeiro' }, { id: '2', label: 'Fevereiro' }, { id: '3', label: 'Março' },
  { id: '4', label: 'Abril' }, { id: '5', label: 'Maio' }, { id: '6', label: 'Junho' },
  { id: '7', label: 'Julho' }, { id: '8', label: 'Agosto' }, { id: '9', label: 'Setembro' },
  { id: '10', label: 'Outubro' }, { id: '11', label: 'Novembro' }, { id: '12', label: 'Dezembro' },
];

const FORMAS_PAGAMENTO = ['PIX', 'TRANSFERENCIA', 'CARTAO', 'BOLETO', 'DINHEIRO'];

const fmtBRL = (val) => `R$ ${Number(val || 0).toFixed(2).replace('.', ',')}`;

const fmtDate = (iso) => {
  if (!iso) return '—';
  const parts = String(iso).split('T')[0].split('-');
  if (parts.length !== 3) return String(iso);
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
};

const currentYM = () => new Date().toISOString().slice(0, 7);
const todayISO = () => new Date().toISOString().slice(0, 10);

export function ExpensesSection({ showToast, onRefreshDRE }) {
  const [expenses, setExpenses] = useState([]);
  const [costCenters, setCostCenters] = useState([]);
  const [loading, setLoading] = useState(false);

  const now = new Date();
  const [anoFiltro, setAnoFiltro] = useState(String(now.getFullYear()));
  const [mesFiltro, setMesFiltro] = useState('');
  const [catFiltro, setCatFiltro] = useState('');
  const [ccFiltro, setCcFiltro] = useState('');
  const [sitFiltro, setSitFiltro] = useState('');
  const [busca, setBusca] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    categoria: 'Aluguel',
    descricao: '',
    valor_previsto: '',
    valor_pago: '',
    data_competencia: todayISO(),
    data_vencimento: todayISO(),
    data_pagamento: '',
    situacao: 'EM_ABERTO',
    forma_pagamento: 'PIX',
    centro_custo_id: '',
    recorrente: false,
    recorrencia_meses: 1,
    total_parcelas: 1,
    observacoes: '',
  });

  const buildQuery = () => {
    const p = new URLSearchParams();
    if (anoFiltro) p.set('ano', anoFiltro);
    if (mesFiltro) p.set('mes', mesFiltro);
    if (catFiltro) p.set('categoria', catFiltro);
    if (ccFiltro) p.set('centro_custo_id', ccFiltro);
    if (sitFiltro) p.set('situacao', sitFiltro);
    if (busca.trim()) p.set('busca', busca.trim());
    return p.toString();
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [expData, ccData] = await Promise.all([
        api.getExpenses(buildQuery()),
        api.getCostCenters(),
      ]);
      setExpenses(Array.isArray(expData) ? expData : []);
      setCostCenters(Array.isArray(ccData) ? ccData : []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [anoFiltro, mesFiltro, catFiltro, ccFiltro, sitFiltro]);

  const openNew = () => {
    setEditing(null);
    setForm({
      categoria: 'Aluguel',
      descricao: '',
      valor_previsto: '',
      valor_pago: '',
      data_competencia: todayISO(),
      data_vencimento: todayISO(),
      data_pagamento: '',
      situacao: 'EM_ABERTO',
      forma_pagamento: 'PIX',
      centro_custo_id: '',
      recorrente: false,
      recorrencia_meses: 1,
      total_parcelas: 1,
      observacoes: '',
    });
    setShowModal(true);
  };

  const openEdit = (exp) => {
    setEditing(exp);
    setForm({
      categoria: exp.categoria || 'Outros',
      descricao: exp.descricao || '',
      valor_previsto: String(exp.valor_previsto ?? exp.valor ?? ''),
      valor_pago: exp.valor_pago ? String(exp.valor_pago) : '',
      data_competencia: exp.data_competencia || todayISO(),
      data_vencimento: exp.data_vencimento || exp.data_competencia || todayISO(),
      data_pagamento: exp.data_pagamento || '',
      situacao: exp.situacao || (exp.pago ? 'PAGO' : 'EM_ABERTO'),
      forma_pagamento: exp.forma_pagamento || 'PIX',
      centro_custo_id: exp.centro_custo_id ? String(exp.centro_custo_id) : '',
      recorrente: Boolean(exp.recorrente),
      recorrencia_meses: 1,
      total_parcelas: 1,
      observacoes: exp.observacoes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        categoria: form.categoria,
        descricao: form.descricao,
        valor_previsto: parseFloat(form.valor_previsto),
        valor_pago: form.valor_pago !== '' ? parseFloat(form.valor_pago) : 0,
        data_competencia: form.data_competencia,
        data_vencimento: form.data_vencimento || form.data_competencia,
        data_pagamento: form.situacao === 'PAGO' ? (form.data_pagamento || todayISO()) : null,
        situacao: form.situacao,
        pago: form.situacao === 'PAGO',
        forma_pagamento: form.forma_pagamento,
        centro_custo_id: form.centro_custo_id ? parseInt(form.centro_custo_id, 10) : null,
        observacoes: form.observacoes || null,
      };
      if (editing) {
        await api.updateExpense(editing.id, payload);
        showToast('Despesa atualizada com sucesso!');
      } else {
        const res = await api.createExpense({
          ...payload,
          recorrente: Boolean(form.recorrente),
          recorrencia_meses: form.recorrente ? parseInt(form.recorrencia_meses || 1, 10) : 1,
          total_parcelas: !form.recorrente ? parseInt(form.total_parcelas || 1, 10) : 1,
        });
        showToast(
          res.parcelas_criadas > 1
            ? `${res.parcelas_criadas} lançamentos de despesa criados!`
            : 'Despesa cadastrada com sucesso!'
        );
      }
      setShowModal(false);
      loadData();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleQuickPay = async (exp) => {
    try {
      await api.updateExpense(exp.id, {
        situacao: 'PAGO',
        pago: true,
        valor_pago: exp.valor_previsto ?? exp.valor,
        data_pagamento: todayISO(),
      });
      showToast('Despesa marcada como PAGA!');
      loadData();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDelete = async (exp) => {
    if (!window.confirm(`Excluir a despesa '${exp.descricao}'?`)) return;
    try {
      await api.deleteExpense(exp.id);
      showToast('Despesa excluída!');
      loadData();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const totalPrevisto = expenses.reduce((s, d) => s + Number(d.valor_previsto ?? d.valor ?? 0), 0);
  const totalPago = expenses.filter(d => d.pago).reduce((s, d) => s + Number(d.valor_pago || d.valor || 0), 0);
  const totalAberto = expenses.filter(d => !d.pago).reduce((s, d) => s + Number(d.valor_previsto ?? d.valor ?? 0), 0);

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Despesas & Contas a Pagar</h3>
          <p className="text-xs text-slate-500">Alimenta automaticamente as Despesas Operacionais no DRE e os Centros de Custo.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => api.exportExpensesCsv(buildQuery()).catch(err => showToast(err.message, 'error'))}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" /> Exportar CSV
          </button>
          <button
            type="button"
            onClick={openNew}
            className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" /> Nova Despesa
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-medium">Total Previsto (Filtro)</span>
          <div className="text-xl font-bold text-slate-800 mt-1">{fmtBRL(totalPrevisto)}</div>
        </div>
        <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 shadow-sm">
          <span className="text-xs text-emerald-700 font-medium">Total Pago</span>
          <div className="text-xl font-bold text-emerald-900 mt-1">{fmtBRL(totalPago)}</div>
        </div>
        <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 shadow-sm">
          <span className="text-xs text-amber-800 font-medium">Em Aberto</span>
          <div className="text-xl font-bold text-amber-900 mt-1">{fmtBRL(totalAberto)}</div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <input
          type="number"
          placeholder="Ano"
          value={anoFiltro}
          onChange={e => setAnoFiltro(e.target.value)}
          className="px-3 py-1.5 border rounded-lg text-xs"
        />
        <select value={mesFiltro} onChange={e => setMesFiltro(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
          <option value="">Todos os meses</option>
          {MESES_OPTS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
        <select value={catFiltro} onChange={e => setCatFiltro(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
          <option value="">Todas categorias</option>
          {CATEGORIAS_DESPESA.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={ccFiltro} onChange={e => setCcFiltro(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
          <option value="">Todos centros de custo</option>
          {costCenters.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
        <select value={sitFiltro} onChange={e => setSitFiltro(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
          <option value="">Todas situações</option>
          <option value="EM_ABERTO">Em Aberto</option>
          <option value="PAGO">Pago</option>
        </select>
        <div className="flex gap-1">
          <input
            type="text"
            placeholder="Buscar descrição..."
            value={busca}
            onChange={e => setBusca(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadData()}
            className="w-full px-3 py-1.5 border rounded-lg text-xs"
          />
          <button type="button" onClick={loadData} className="px-2.5 bg-slate-100 rounded-lg text-xs font-semibold hover:bg-slate-200">
            <Filter className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-600">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-3 py-3">Vencimento</th>
              <th className="px-3 py-3">Competência</th>
              <th className="px-3 py-3">Categoria / Centro</th>
              <th className="px-3 py-3">Descrição</th>
              <th className="px-3 py-3 text-right">Previsto</th>
              <th className="px-3 py-3 text-right">Pago</th>
              <th className="px-3 py-3">Situação</th>
              <th className="px-3 py-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan="8" className="px-4 py-8 text-center text-slate-400">Carregando despesas...</td></tr>
            ) : expenses.length === 0 ? (
              <tr><td colSpan="8" className="px-4 py-8 text-center text-slate-400">Nenhuma despesa encontrada para os filtros aplicados.</td></tr>
            ) : expenses.map(exp => (
              <tr key={exp.id} className="hover:bg-slate-50">
                <td className="px-3 py-2.5 whitespace-nowrap font-medium text-slate-800">{fmtDate(exp.data_vencimento || exp.data_competencia)}</td>
                <td className="px-3 py-2.5 whitespace-nowrap">{fmtDate(exp.data_competencia)}</td>
                <td className="px-3 py-2.5">
                  <span className="font-semibold text-slate-800 block">{exp.categoria}</span>
                  <span className="text-[11px] text-slate-400">{exp.centro_custo_nome || 'Sem centro'}</span>
                </td>
                <td className="px-3 py-2.5">
                  <span className="text-slate-800 font-medium">{exp.descricao}</span>
                  {exp.recorrente && <span className="ml-1.5 px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 text-indigo-700 font-semibold">Recorrente</span>}
                  {exp.observacoes && <span className="block text-[11px] text-slate-400 truncate max-w-xs">{exp.observacoes}</span>}
                </td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap">{fmtBRL(exp.valor_previsto ?? exp.valor)}</td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap font-semibold text-emerald-700">
                  {exp.pago ? fmtBRL(exp.valor_pago || exp.valor) : '—'}
                </td>
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${exp.pago ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                    {exp.pago ? `PAGO (${fmtDate(exp.data_pagamento)})` : 'EM ABERTO'}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-right whitespace-nowrap space-x-1">
                  {!exp.pago && (
                    <button type="button" onClick={() => handleQuickPay(exp)} title="Dar baixa como pago" className="p-1.5 text-emerald-700 hover:bg-emerald-50 rounded">
                      <CheckCircle className="w-4 h-4" />
                    </button>
                  )}
                  <button type="button" onClick={() => openEdit(exp)} title="Editar despesa" className="p-1.5 text-slate-600 hover:bg-slate-100 rounded">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button type="button" onClick={() => handleDelete(exp)} title="Excluir despesa" className="p-1.5 text-red-600 hover:bg-red-50 rounded">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal Criar / Editar Despesa */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-3 border-b mb-4">
              <h3 className="font-bold text-slate-800">{editing ? 'Editar Despesa' : 'Nova Despesa Operacional'}</h3>
              <button type="button" onClick={() => setShowModal(false)} className="p-1 text-slate-400 hover:text-slate-700"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Categoria</label>
                  <select value={form.categoria} onChange={e => setForm({ ...form, categoria: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                    {CATEGORIAS_DESPESA.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Centro de Custo</label>
                  <select value={form.centro_custo_id} onChange={e => setForm({ ...form, centro_custo_id: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                    <option value="">Sem centro (classificar)</option>
                    {costCenters.map(c => <option key={c.id} value={c.id}>{c.nome} ({c.tipo})</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Descrição</label>
                <input type="text" required value={form.descricao} onChange={e => setForm({ ...form, descricao: e.target.value })} placeholder="Ex: Aluguel do ateliê, Compra de tintas..." className="w-full px-3 py-2 border rounded-lg" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Vencimento</label>
                  <input type="date" required value={form.data_vencimento} onChange={e => setForm({ ...form, data_vencimento: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Competência</label>
                  <input type="date" required value={form.data_competencia} onChange={e => setForm({ ...form, data_competencia: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Valor Previsto (R$)</label>
                  <input type="number" step="0.01" min="0.01" required value={form.valor_previsto} onChange={e => setForm({ ...form, valor_previsto: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Situação</label>
                  <select value={form.situacao} onChange={e => setForm({ ...form, situacao: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                    <option value="EM_ABERTO">Em Aberto</option>
                    <option value="PAGO">Pago</option>
                  </select>
                </div>
              </div>

              {form.situacao === 'PAGO' && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                  <div>
                    <label className="block font-semibold text-emerald-900 mb-1">Valor Pago (R$)</label>
                    <input type="number" step="0.01" min="0" value={form.valor_pago} onChange={e => setForm({ ...form, valor_pago: e.target.value })} placeholder={form.valor_previsto} className="w-full px-3 py-2 border rounded-lg bg-white" />
                  </div>
                  <div>
                    <label className="block font-semibold text-emerald-900 mb-1">Data do Pagamento</label>
                    <input type="date" value={form.data_pagamento} onChange={e => setForm({ ...form, data_pagamento: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white" />
                  </div>
                  <div>
                    <label className="block font-semibold text-emerald-900 mb-1">Forma</label>
                    <select value={form.forma_pagamento} onChange={e => setForm({ ...form, forma_pagamento: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                      {FORMAS_PAGAMENTO.map(f => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                </div>
              )}

              {!editing && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 items-center">
                  <label className="flex items-center gap-2 font-semibold text-slate-700 cursor-pointer">
                    <input type="checkbox" checked={form.recorrente} onChange={e => setForm({ ...form, recorrente: e.target.checked })} />
                    Despesa recorrente (fixa mensal)
                  </label>
                  {form.recorrente ? (
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">Repetir por (meses)</label>
                      <input type="number" min="1" max="36" value={form.recorrencia_meses} onChange={e => setForm({ ...form, recorrencia_meses: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
                    </div>
                  ) : (
                    <div>
                      <label className="block font-semibold text-slate-600 mb-1">Parcelar em (vezes)</label>
                      <input type="number" min="1" max="36" value={form.total_parcelas} onChange={e => setForm({ ...form, total_parcelas: e.target.value })} className="w-full px-3 py-1.5 border rounded-lg bg-white" />
                    </div>
                  )}
                  <span className="text-[11px] text-slate-500">
                    {form.recorrente ? 'Repete o valor integral mensalmente.' : 'Divide o valor total entre as parcelas.'}
                  </span>
                </div>
              )}

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Observações</label>
                <textarea rows="2" value={form.observacoes} onChange={e => setForm({ ...form, observacoes: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border text-slate-600 hover:bg-slate-50 font-semibold">Cancelar</button>
                <button type="submit" className="px-4 py-2 rounded-lg bg-amber-700 text-white hover:bg-amber-800 font-semibold">Salvar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export function CostCentersSection({ showToast }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ano, setAno] = useState(String(new Date().getFullYear()));
  const [mes, setMes] = useState('');
  const [tipo, setTipo] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [newCcNome, setNewCcNome] = useState('');

  const loadReport = async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (ano) p.set('ano', ano);
      if (mes) p.set('mes', mes);
      if (tipo) p.set('tipo', tipo);
      const data = await api.getCostCentersReport(p.toString());
      setReport(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, [ano, mes, tipo]);

  const handleCreateCenter = async (e) => {
    e.preventDefault();
    if (!newCcNome.trim()) return;
    try {
      await api.createCostCenter({ nome: newCcNome.trim(), tipo: 'GERAL' });
      setNewCcNome('');
      showToast('Centro de custo criado!');
      loadReport();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Centros de Custo (Gerais e por Curso)</h3>
          <p className="text-xs text-slate-500">Receitas, custos (professores, comissões, materiais), resultado e % do total — Previsto vs Realizado.</p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input type="number" value={ano} onChange={e => setAno(e.target.value)} className="w-24 px-3 py-1.5 border rounded-lg text-xs" />
          <select value={mes} onChange={e => setMes(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
            <option value="">Ano inteiro</option>
            {MESES_OPTS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          <select value={tipo} onChange={e => setTipo(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs bg-white">
            <option value="">Todos (Cursos + Gerais)</option>
            <option value="CURSO">Apenas Cursos</option>
            <option value="GERAL">Apenas Gerais</option>
          </select>
        </div>
      </div>

      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs text-slate-500 font-medium">Receita (Realizada / Prevista)</span>
            <div className="text-lg font-bold text-emerald-700 mt-1">
              {fmtBRL(report.total_receita_realizada)} <span className="text-xs font-normal text-slate-400">/ {fmtBRL(report.total_receita_prevista)}</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs text-slate-500 font-medium">Custo (Realizado / Previsto)</span>
            <div className="text-lg font-bold text-red-700 mt-1">
              {fmtBRL(report.total_custo_realizado)} <span className="text-xs font-normal text-slate-400">/ {fmtBRL(report.total_custo_previsto)}</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs text-slate-500 font-medium">Resultado (Realizado / Previsto)</span>
            <div className="text-lg font-bold text-slate-800 mt-1">
              {fmtBRL(report.total_resultado_realizado)} <span className="text-xs font-normal text-slate-400">/ {fmtBRL(report.total_resultado_previsto)}</span>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-600">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-3 py-3">Centro de Custo</th>
              <th className="px-3 py-3 text-right">Rec. Prevista</th>
              <th className="px-3 py-3 text-right">Custo Previsto</th>
              <th className="px-3 py-3 text-right">Res. Previsto</th>
              <th className="px-3 py-3 text-right">Rec. Realizada</th>
              <th className="px-3 py-3 text-right">Custo Realizado</th>
              <th className="px-3 py-3 text-right">Res. Realizado</th>
              <th className="px-3 py-3 text-right">% Receita</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan="8" className="px-4 py-8 text-center text-slate-400">Calculando centros de custo...</td></tr>
            ) : !report || report.centros.length === 0 ? (
              <tr><td colSpan="8" className="px-4 py-8 text-center text-slate-400">Nenhum dado encontrado.</td></tr>
            ) : report.centros.map(c => (
              <React.Fragment key={c.centro_custo_id}>
                <tr
                  onClick={() => setExpandedId(expandedId === c.centro_custo_id ? null : c.centro_custo_id)}
                  className="hover:bg-amber-50/40 cursor-pointer"
                >
                  <td className="px-3 py-2.5 font-semibold text-slate-800 flex items-center gap-1.5">
                    <ChevronDown className={`w-3.5 h-3.5 transition ${expandedId === c.centro_custo_id ? 'rotate-180' : ''}`} />
                    <span>{c.nome}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${c.tipo === 'CURSO' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>{c.tipo}</span>
                  </td>
                  <td className="px-3 py-2.5 text-right">{fmtBRL(c.receita_prevista_total)}</td>
                  <td className="px-3 py-2.5 text-right text-red-700">{fmtBRL(c.custo_previsto_total)}</td>
                  <td className="px-3 py-2.5 text-right font-semibold">{fmtBRL(c.resultado_previsto_total)}</td>
                  <td className="px-3 py-2.5 text-right text-emerald-700 font-semibold">{fmtBRL(c.receita_realizada_total)}</td>
                  <td className="px-3 py-2.5 text-right text-red-700">{fmtBRL(c.custo_realizado_total)}</td>
                  <td className={`px-3 py-2.5 text-right font-bold ${c.resultado_realizado_total >= 0 ? 'text-emerald-800' : 'text-red-700'}`}>{fmtBRL(c.resultado_realizado_total)}</td>
                  <td className="px-3 py-2.5 text-right">{c.percentual_receita_realizada.toFixed(1)}% <span className="text-[10px] text-slate-400">({c.percentual_receita_prevista.toFixed(1)}% p)</span></td>
                </tr>
                {expandedId === c.centro_custo_id && c.meses.length > 0 && (
                  <tr>
                    <td colSpan="8" className="bg-slate-50 px-6 py-3">
                      <div className="text-[11px] font-bold text-slate-700 mb-2">Detalhamento Mês a Mês — {c.nome}</div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {c.meses.map(m => (
                          <div key={m.competencia} className="bg-white border rounded-lg p-2.5 text-[11px]">
                            <div className="font-bold text-slate-800 mb-1">{m.competencia}</div>
                            <div className="flex justify-between"><span>Previsto:</span><span>{fmtBRL(m.receita_prevista)} - {fmtBRL(m.custo_previsto)} = <b>{fmtBRL(m.resultado_previsto)}</b></span></div>
                            <div className="flex justify-between text-emerald-800"><span>Realizado:</span><span>{fmtBRL(m.receita_realizada)} - {fmtBRL(m.custo_realizado)} = <b>{fmtBRL(m.resultado_realizado)}</b></span></div>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleCreateCenter} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap gap-2 items-center">
        <span className="text-xs font-semibold text-slate-700">Novo Centro Geral:</span>
        <input
          type="text"
          value={newCcNome}
          onChange={e => setNewCcNome(e.target.value)}
          placeholder="Nome do centro de custo..."
          className="px-3 py-1.5 border rounded-lg text-xs flex-1 min-w-[200px]"
        />
        <button type="submit" className="px-4 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900">
          Criar Centro
        </button>
      </form>
    </div>
  );
}

export function TeacherPayoutsSection({ showToast, teachers, courses, onRefreshDRE }) {
  const [rules, setRules] = useState([]);
  const [closings, setClosings] = useState([]);
  const [changeLogs, setChangeLogs] = useState([]);
  const [competencia, setCompetencia] = useState(currentYM());
  const [expandedClosing, setExpandedClosing] = useState(null);
  const [payModal, setPayModal] = useState(null);
  const [payForm, setPayForm] = useState({
    valor_pago: '',
    data_pagamento: todayISO(),
    forma_pagamento: 'PIX',
    conciliado_extrato: false,
    referencia_extrato: '',
    observacoes: '',
  });
  const [ruleForm, setRuleForm] = useState({
    professor_id: '',
    curso_id: '',
    modalidade: 'POR_PRESENCA',
    valor_por_presenca: '15.00',
    percentual_curso: '30',
    pagamento_percentual_modo: 'PARCELADO_MENSAL',
    valor_fixo_mensal: '0',
    pagar_experimental: false,
    pagar_cortesia: false,
  });

  const loadAll = async () => {
    try {
      const [r, c, logs] = await Promise.all([
        api.getTeacherRules(),
        api.getTeacherClosings(competencia),
        api.getAttendanceChangeLogs(competencia),
      ]);
      setRules(r || []);
      setClosings(c || []);
      setChangeLogs(logs || []);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  useEffect(() => {
    loadAll();
  }, [competencia]);

  const handleSaveRule = async (e) => {
    e.preventDefault();
    if (!ruleForm.professor_id) {
      showToast('Selecione o professor.', 'error');
      return;
    }
    try {
      await api.upsertTeacherRule({
        professor_id: parseInt(ruleForm.professor_id, 10),
        curso_id: ruleForm.curso_id ? parseInt(ruleForm.curso_id, 10) : null,
        modalidade: ruleForm.modalidade,
        valor_por_presenca: parseFloat(ruleForm.valor_por_presenca || 0),
        percentual_curso: parseFloat(ruleForm.percentual_curso || 0),
        pagamento_percentual_modo: ruleForm.pagamento_percentual_modo,
        valor_fixo_mensal: parseFloat(ruleForm.valor_fixo_mensal || 0),
        pagar_experimental: Boolean(ruleForm.pagar_experimental),
        pagar_cortesia: Boolean(ruleForm.pagar_cortesia),
        ativo: true,
      });
      showToast('Regra de remuneração salva!');
      loadAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleGenerate = async () => {
    try {
      await api.generateTeacherClosings({ competencia });
      showToast(`Fechamento de ${competencia} calculado com base na chamada e contratos!`);
      loadAll();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const openPay = (closing) => {
    setPayModal(closing);
    setPayForm({
      valor_pago: String(closing.saldo_a_pagar || closing.valor_total || 0),
      data_pagamento: todayISO(),
      forma_pagamento: 'PIX',
      conciliado_extrato: false,
      referencia_extrato: '',
      observacoes: '',
    });
  };

  const handlePaySubmit = async (e) => {
    e.preventDefault();
    try {
      await api.payTeacherClosing(payModal.id, {
        ...payForm,
        valor_pago: parseFloat(payForm.valor_pago),
      });
      showToast('Pagamento do professor registrado e lançado no centro de custo!');
      setPayModal(null);
      loadAll();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleReopen = async (id) => {
    try {
      await api.reopenTeacherClosing(id);
      showToast('Fechamento reaberto para ajustes na chamada.');
      loadAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* Regras */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Regras de Remuneração por Professor e Curso</h3>
          <p className="text-xs text-slate-500">Configure por presença (ex: R$ 15/aluno), percentual sobre o curso (único ou parcelado mês a mês) ou fixo mensal.</p>
        </div>

        <form onSubmit={handleSaveRule} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Professor</label>
            <select required value={ruleForm.professor_id} onChange={e => setRuleForm({ ...ruleForm, professor_id: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white">
              <option value="">-- Selecionar --</option>
              {teachers.map(t => <option key={t.id} value={t.id}>{t.nome}</option>)}
            </select>
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Curso</label>
            <select value={ruleForm.curso_id} onChange={e => setRuleForm({ ...ruleForm, curso_id: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white">
              <option value="">Padrão (todos os cursos)</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Modalidade</label>
            <select value={ruleForm.modalidade} onChange={e => setRuleForm({ ...ruleForm, modalidade: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white">
              <option value="POR_PRESENCA">Por Presença (Chamada)</option>
              <option value="PERCENTUAL">Percentual sobre Curso (%)</option>
              <option value="FIXO_MENSAL">Fixo Mensal (R$)</option>
            </select>
          </div>

          {ruleForm.modalidade === 'POR_PRESENCA' && (
            <div>
              <label className="block font-semibold text-slate-600 mb-1">Valor por Presença (R$)</label>
              <input type="number" step="0.01" min="0" value={ruleForm.valor_por_presenca} onChange={e => setRuleForm({ ...ruleForm, valor_por_presenca: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white" />
            </div>
          )}
          {ruleForm.modalidade === 'PERCENTUAL' && (
            <>
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Percentual (%)</label>
                <input type="number" step="0.1" min="0" max="100" value={ruleForm.percentual_curso} onChange={e => setRuleForm({ ...ruleForm, percentual_curso: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white" />
              </div>
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Forma de Repasse do %</label>
                <select value={ruleForm.pagamento_percentual_modo} onChange={e => setRuleForm({ ...ruleForm, pagamento_percentual_modo: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white">
                  <option value="PARCELADO_MENSAL">Parcelado mês a mês (junto às parcelas)</option>
                  <option value="UNICO">Pagamento único no início do contrato</option>
                </select>
              </div>
            </>
          )}
          {ruleForm.modalidade === 'FIXO_MENSAL' && (
            <div>
              <label className="block font-semibold text-slate-600 mb-1">Valor Fixo Mensal (R$)</label>
              <input type="number" step="0.01" min="0" value={ruleForm.valor_fixo_mensal} onChange={e => setRuleForm({ ...ruleForm, valor_fixo_mensal: e.target.value })} className="w-full px-2.5 py-2 border rounded-lg bg-white" />
            </div>
          )}

          <div className="flex items-center gap-4 sm:col-span-2">
            <label className="flex items-center gap-1.5 text-slate-700 cursor-pointer">
              <input type="checkbox" checked={ruleForm.pagar_experimental} onChange={e => setRuleForm({ ...ruleForm, pagar_experimental: e.target.checked })} />
              Pagar aula experimental
            </label>
            <label className="flex items-center gap-1.5 text-slate-700 cursor-pointer">
              <input type="checkbox" checked={ruleForm.pagar_cortesia} onChange={e => setRuleForm({ ...ruleForm, pagar_cortesia: e.target.checked })} />
              Pagar cortesia
            </label>
          </div>
          <div className="sm:col-span-2 flex justify-end items-end">
            <button type="submit" className="px-4 py-2 bg-amber-700 text-white rounded-lg font-semibold hover:bg-amber-800">Salvar Regra</button>
          </div>
        </form>

        {rules.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 border-y">
                <tr>
                  <th className="px-3 py-2">Professor</th>
                  <th className="px-3 py-2">Curso</th>
                  <th className="px-3 py-2">Modalidade</th>
                  <th className="px-3 py-2">Parâmetro</th>
                  <th className="px-3 py-2">Exceções</th>
                  <th className="px-3 py-2 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rules.map(r => (
                  <tr key={r.id}>
                    <td className="px-3 py-2 font-semibold text-slate-800">{r.professor_nome}</td>
                    <td className="px-3 py-2">{r.curso_nome}</td>
                    <td className="px-3 py-2">{r.modalidade}</td>
                    <td className="px-3 py-2 font-medium">
                      {r.modalidade === 'POR_PRESENCA' && `${fmtBRL(r.valor_por_presenca)} / presença`}
                      {r.modalidade === 'PERCENTUAL' && `${r.percentual_curso}% (${r.pagamento_percentual_modo})`}
                      {r.modalidade === 'FIXO_MENSAL' && `${fmtBRL(r.valor_fixo_mensal)} / mês`}
                    </td>
                    <td className="px-3 py-2 text-[11px]">
                      Exp: {r.pagar_experimental ? 'Sim' : 'Não'} • Cort: {r.pagar_cortesia ? 'Sim' : 'Não'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" onClick={() => api.deleteTeacherRule(r.id).then(loadAll)} className="text-red-600 hover:text-red-800 p-1">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Fechamento Mensal */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <h3 className="font-bold text-slate-800 text-base">Fechamento Mensal de Professores</h3>
            <p className="text-xs text-slate-500">Ao fechar o mês, alterações na chamada ficam bloqueadas (apenas Direção edita com justificativa).</p>
          </div>
          <div className="flex items-center gap-2">
            <input type="month" value={competencia} onChange={e => setCompetencia(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs" />
            <button type="button" onClick={handleGenerate} className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900">
              Gerar / Atualizar Fechamento
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 border-y">
              <tr>
                <th className="px-3 py-2">Professor</th>
                <th className="px-3 py-2 text-center">Aulas / Presenças</th>
                <th className="px-3 py-2 text-right">Por Presença</th>
                <th className="px-3 py-2 text-right">Percentual</th>
                <th className="px-3 py-2 text-right">Fixo</th>
                <th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2 text-right">Pago / Saldo</th>
                <th className="px-3 py-2">Status & Extrato</th>
                <th className="px-3 py-2 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {closings.length === 0 ? (
                <tr><td colSpan="9" className="px-4 py-6 text-center text-slate-400">Clique em "Gerar / Atualizar Fechamento" para calcular esta competência.</td></tr>
              ) : closings.map(c => (
                <React.Fragment key={c.id}>
                  <tr className="hover:bg-slate-50">
                    <td className="px-3 py-2.5 font-semibold text-slate-800">
                      <button type="button" onClick={() => setExpandedClosing(expandedClosing === c.id ? null : c.id)} className="flex items-center gap-1 hover:text-amber-700">
                        <ChevronDown className={`w-3.5 h-3.5 ${expandedClosing === c.id ? 'rotate-180' : ''}`} />
                        {c.professor_nome}
                      </button>
                    </td>
                    <td className="px-3 py-2.5 text-center">{c.total_aulas_dadas} aulas • {c.total_presencas} pres.</td>
                    <td className="px-3 py-2.5 text-right">{fmtBRL(c.valor_por_presenca_total)}</td>
                    <td className="px-3 py-2.5 text-right">{fmtBRL(c.valor_percentual_total)}</td>
                    <td className="px-3 py-2.5 text-right">{fmtBRL(c.valor_fixo_total)}</td>
                    <td className="px-3 py-2.5 text-right font-bold text-slate-800">{fmtBRL(c.valor_total)}</td>
                    <td className="px-3 py-2.5 text-right">
                      <span className="text-emerald-700 block font-semibold">{fmtBRL(c.valor_pago)}</span>
                      <span className="text-[11px] text-amber-800">Saldo: {fmtBRL(c.saldo_a_pagar)}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${c.status === 'PAGO' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                        {c.status}
                      </span>
                      {c.conciliado_extrato && (
                        <span className="block text-[10px] text-emerald-700 mt-0.5">Extrato: {c.referencia_extrato || 'Conciliado'}</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right whitespace-nowrap space-x-1">
                      {c.status !== 'PAGO' && (
                        <button type="button" onClick={() => openPay(c)} className="px-2.5 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold hover:bg-emerald-700">
                          Pagar
                        </button>
                      )}
                      {c.status === 'FECHADO' && c.valor_pago === 0 && (
                        <button type="button" onClick={() => handleReopen(c.id)} className="px-2 py-1 bg-slate-200 text-slate-700 rounded text-[11px] font-semibold hover:bg-slate-300">
                          Reabrir
                        </button>
                      )}
                    </td>
                  </tr>
                  {expandedClosing === c.id && (
                    <tr>
                      <td colSpan="9" className="bg-slate-50 px-5 py-3">
                        <div className="text-[11px] font-bold text-slate-700 mb-2">Detalhamento por Turma e Aluno</div>
                        {(!c.detalhes || c.detalhes.length === 0) ? (
                          <p className="text-[11px] text-slate-400">Sem lançamentos detalhados.</p>
                        ) : (
                          <div className="max-h-60 overflow-y-auto space-y-1">
                            {c.detalhes.map((d, i) => (
                              <div key={i} className="bg-white border rounded px-3 py-1.5 flex justify-between items-center text-[11px]">
                                <span><b>{fmtDate(d.data)}</b> • {d.curso_nome} ({d.turma_nome}) • {d.aluno_nome} — <span className="text-slate-500">{d.observacao}</span></span>
                                <span className="font-bold text-slate-800">{fmtBRL(d.valor)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {changeLogs.length > 0 && (
        <div className="bg-white rounded-xl border border-amber-200 p-4 shadow-sm">
          <h4 className="font-bold text-amber-900 text-xs mb-2">Histórico de Alterações na Chamada ({competencia})</h4>
          <div className="space-y-1 text-[11px] text-slate-600">
            {changeLogs.map(lg => (
              <div key={lg.id} className="border-b border-slate-100 pb-1">
                Aula #{lg.lesson_id} • Aluno #{lg.aluno_id}: {lg.status_anterior || 'NOVO'} → <b>{lg.status_novo}</b> por {lg.alterado_por_nome} — <i>{lg.motivo}</i>
              </div>
            ))}
          </div>
        </div>
      )}

      {payModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl">
            <h3 className="font-bold text-slate-800 mb-3">Pagar Professor — {payModal.professor_nome}</h3>
            <form onSubmit={handlePaySubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Valor Pago (R$)</label>
                <input type="number" step="0.01" min="0.01" required value={payForm.valor_pago} onChange={e => setPayForm({ ...payForm, valor_pago: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Data</label>
                  <input type="date" required value={payForm.data_pagamento} onChange={e => setPayForm({ ...payForm, data_pagamento: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Forma</label>
                  <select value={payForm.forma_pagamento} onChange={e => setPayForm({ ...payForm, forma_pagamento: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                    {FORMAS_PAGAMENTO.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
              </div>
              <label className="flex items-center gap-2 font-semibold text-slate-700">
                <input type="checkbox" checked={payForm.conciliado_extrato} onChange={e => setPayForm({ ...payForm, conciliado_extrato: e.target.checked })} />
                Conciliado com o extrato bancário
              </label>
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Referência / ID Extrato</label>
                <input type="text" value={payForm.referencia_extrato} onChange={e => setPayForm({ ...payForm, referencia_extrato: e.target.value })} placeholder="Ex: PIX BANCO 14/11" className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setPayModal(null)} className="px-4 py-2 border rounded-lg">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold">Confirmar Pagamento</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export function CommercialPayoutSection({ showToast, onRefreshDRE }) {
  const [config, setConfig] = useState({
    nome_responsavel: 'Comercial HB',
    valor_fixo_mensal: 0,
    comissao_por_matricula: 0,
    percentual_sobre_vendas: 0,
    ativo: true,
  });
  const [closings, setClosings] = useState([]);
  const [competencia, setCompetencia] = useState(currentYM());

  const loadData = async () => {
    try {
      const [cfg, cls] = await Promise.all([api.getCommercialConfig(), api.getCommercialClosings()]);
      if (cfg) setConfig(cfg);
      setClosings(cls || []);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    try {
      await api.updateCommercialConfig({
        ...config,
        valor_fixo_mensal: parseFloat(config.valor_fixo_mensal || 0),
        comissao_por_matricula: parseFloat(config.comissao_por_matricula || 0),
        percentual_sobre_vendas: parseFloat(config.percentual_sobre_vendas || 0),
      });
      showToast('Configuração do Comercial salva!');
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleGenerate = async () => {
    try {
      await api.generateCommercialClosing(competencia);
      showToast(`Fechamento do Comercial gerado para ${competencia}!`);
      loadData();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handlePay = async (p) => {
    try {
      await api.payCommercialClosing(p.id, {
        valor_pago: p.saldo > 0 ? p.saldo : p.total_devido,
        data_pagamento: todayISO(),
        forma_pagamento: 'PIX',
      });
      showToast('Pagamento do Comercial registrado!');
      loadData();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h3 className="font-bold text-slate-800 text-base">Remuneração do Comercial</h3>
        <form onSubmit={handleSaveConfig} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Responsável / Equipe</label>
            <input type="text" required value={config.nome_responsavel} onChange={e => setConfig({ ...config, nome_responsavel: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Fixo Mensal (R$)</label>
            <input type="number" step="0.01" min="0" value={config.valor_fixo_mensal} onChange={e => setConfig({ ...config, valor_fixo_mensal: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Comissão / Matrícula Nova (R$)</label>
            <input type="number" step="0.01" min="0" value={config.comissao_por_matricula} onChange={e => setConfig({ ...config, comissao_por_matricula: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">% sobre Vendas do Mês</label>
            <input type="number" step="0.1" min="0" max="100" value={config.percentual_sobre_vendas} onChange={e => setConfig({ ...config, percentual_sobre_vendas: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
          </div>
          <div className="sm:col-span-2 lg:col-span-4 flex justify-end">
            <button type="submit" className="px-4 py-2 bg-amber-700 text-white rounded-lg font-semibold hover:bg-amber-800">Salvar Regra do Comercial</button>
          </div>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <h4 className="font-bold text-slate-800 text-sm">Fechamentos Mensais — Comercial</h4>
          <div className="flex gap-2 items-center">
            <input type="month" value={competencia} onChange={e => setCompetencia(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs" />
            <button type="button" onClick={handleGenerate} className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900">Gerar Fechamento</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 border-y">
              <tr>
                <th className="px-3 py-2">Competência</th>
                <th className="px-3 py-2 text-center">Matrículas Novas</th>
                <th className="px-3 py-2 text-right">Vendas do Mês</th>
                <th className="px-3 py-2 text-right">Fixo + Comissão + %</th>
                <th className="px-3 py-2 text-right">Total Devido</th>
                <th className="px-3 py-2 text-right">Pago / Saldo</th>
                <th className="px-3 py-2 text-right">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {closings.map(c => (
                <tr key={c.id}>
                  <td className="px-3 py-2.5 font-semibold text-slate-800">{c.competencia}</td>
                  <td className="px-3 py-2.5 text-center">{c.qtd_matriculas_novas}</td>
                  <td className="px-3 py-2.5 text-right">{fmtBRL(c.total_vendas_mes)}</td>
                  <td className="px-3 py-2.5 text-right text-[11px]">{fmtBRL(c.valor_fixo)} + {fmtBRL(c.valor_comissao_matriculas)} + {fmtBRL(c.valor_percentual_vendas)}</td>
                  <td className="px-3 py-2.5 text-right font-bold text-slate-800">{fmtBRL(c.total_devido)}</td>
                  <td className="px-3 py-2.5 text-right">{fmtBRL(c.valor_pago)} / <span className="text-amber-800 font-semibold">{fmtBRL(c.saldo)}</span></td>
                  <td className="px-3 py-2.5 text-right">
                    {c.saldo > 0 && c.total_devido > 0 ? (
                      <button type="button" onClick={() => handlePay(c)} className="px-3 py-1 bg-emerald-600 text-white rounded text-[11px] font-semibold">Pagar Saldo</button>
                    ) : (
                      <span className="text-emerald-700 font-bold text-[11px]">{c.status}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function PartnerAtelierSection({ showToast, courses, onRefreshDRE }) {
  const [competencia, setCompetencia] = useState(currentYM());
  const [workshops, setWorkshops] = useState([]);
  const [summary, setSummary] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [wsForm, setWsForm] = useState({
    titulo: '',
    modalidade: 'Esmaltação em Cerâmica',
    professora_parceira: '',
    data_realizacao: todayISO(),
    curso_id: '',
    despesas_materiais: '0',
    observacoes: '',
  });
  const [partInputs, setPartInputs] = useState({});

  const loadAll = async () => {
    try {
      const [ws, sum] = await Promise.all([api.getWorkshops(competencia), api.getWorkshopsSummary(competencia)]);
      setWorkshops(ws || []);
      setSummary(sum);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  useEffect(() => {
    loadAll();
  }, [competencia]);

  const handleCreateWorkshop = async (e) => {
    e.preventDefault();
    try {
      await api.createWorkshop({
        ...wsForm,
        curso_id: wsForm.curso_id ? parseInt(wsForm.curso_id, 10) : null,
        despesas_materiais: parseFloat(wsForm.despesas_materiais || 0),
        percentual_escola: 50,
        percentual_professora: 50,
      });
      showToast('Sessão do Ateliê Parceria criada!');
      setShowCreate(false);
      loadAll();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleAddParticipant = async (wsId) => {
    const inp = partInputs[wsId] || {};
    if (!inp.aluno_nome || !inp.valor_pago) {
      showToast('Informe nome e valor do participante avulso.', 'error');
      return;
    }
    try {
      await api.addWorkshopParticipant(wsId, {
        aluno_nome: inp.aluno_nome,
        telefone: inp.telefone || null,
        valor_pago: parseFloat(inp.valor_pago),
        forma_pagamento: inp.forma_pagamento || 'PIX',
      });
      setPartInputs({ ...partInputs, [wsId]: { aluno_nome: '', valor_pago: '', forma_pagamento: 'PIX' } });
      showToast('Aluno avulso registrado!');
      loadAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handlePayTransfer = async (wsId) => {
    try {
      await api.payWorkshopTransfer(wsId, { data_repasse: todayISO(), forma_repasse: 'PIX' });
      showToast('Repasse de 50% registrado e lançado no centro de custo!');
      loadAll();
      if (onRefreshDRE) onRefreshDRE();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-wrap justify-between items-center gap-3">
        <div>
          <h3 className="font-bold text-slate-800 text-base">Ateliê - Parceria (Esmaltação em Cerâmica, Modelagem em Argila)</h3>
          <p className="text-xs text-slate-500">Controle de alunos avulsos por workshop/data, divisão 50% escola / 50% professora e resumo mensal.</p>
        </div>
        <div className="flex gap-2 items-center">
          <input type="month" value={competencia} onChange={e => setCompetencia(e.target.value)} className="px-3 py-1.5 border rounded-lg text-xs" />
          <button type="button" onClick={() => setShowCreate(true)} className="px-4 py-2 bg-amber-700 text-white rounded-lg text-xs font-semibold hover:bg-amber-800 flex items-center gap-1.5">
            <Plus className="w-4 h-4" /> Novo Workshop / Data
          </button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-xs text-slate-500">Receita Bruta ({summary.total_participantes} avulsos)</span>
            <div className="text-lg font-bold text-slate-800 mt-1">{fmtBRL(summary.receita_total)}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-xs text-slate-500">Parte Escola (50%)</span>
            <div className="text-lg font-bold text-emerald-700 mt-1">{fmtBRL(summary.parte_escola_total)}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border shadow-sm">
            <span className="text-xs text-slate-500">Despesas Materiais</span>
            <div className="text-lg font-bold text-red-700 mt-1">{fmtBRL(summary.despesas_materiais_total)}</div>
          </div>
          <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 shadow-sm">
            <span className="text-xs text-amber-800">Repasse Parceira (Saldo)</span>
            <div className="text-lg font-bold text-amber-900 mt-1">{fmtBRL(summary.saldo_a_repassar)} <span className="text-[11px] font-normal">/ {fmtBRL(summary.valor_repassar_total)}</span></div>
          </div>
          <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 shadow-sm">
            <span className="text-xs text-emerald-800">Resultado Líquido Escola</span>
            <div className="text-lg font-bold text-emerald-900 mt-1">{fmtBRL(summary.resultado_liquido_escola)}</div>
          </div>
        </div>
      )}

      {workshops.map(ws => {
        const inp = partInputs[ws.id] || { aluno_nome: '', valor_pago: '', forma_pagamento: 'PIX' };
        return (
          <div key={ws.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-wrap justify-between items-start gap-3 border-b pb-3">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">{ws.titulo} — <span className="text-amber-700">{ws.modalidade}</span></h4>
                <p className="text-xs text-slate-500">Data: {fmtDate(ws.data_realizacao)} • Parceira: <b>{ws.professora_parceira}</b> • Materiais: {fmtBRL(ws.despesas_materiais)}</p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="text-right mr-2">
                  <div>Receita: <b>{fmtBRL(ws.receita_bruta)}</b> • Escola (50%): <b>{fmtBRL(ws.parte_escola)}</b></div>
                  <div className="text-amber-800">Repasse Parceira ({ws.percentual_professora}%): <b>{fmtBRL(ws.valor_repassar_professora)}</b></div>
                </div>
                {ws.repasse_pago ? (
                  <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full font-bold text-[11px]">Repasse Pago</span>
                ) : (
                  <button type="button" onClick={() => handlePayTransfer(ws.id)} className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700">
                    Registrar Repasse 50%
                  </button>
                )}
                <button type="button" onClick={() => api.deleteWorkshop(ws.id).then(loadAll)} className="p-1.5 text-red-600 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>

            <div className="space-y-1.5">
              {(ws.participantes || []).map(p => (
                <div key={p.id} className="flex justify-between items-center bg-slate-50 px-3 py-1.5 rounded text-xs">
                  <span><b>{p.aluno_nome}</b> {p.telefone ? `(${p.telefone})` : ''} • {p.forma_pagamento}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-emerald-700">{fmtBRL(p.valor_pago)}</span>
                    <button type="button" onClick={() => api.deleteWorkshopParticipant(p.id).then(loadAll)} className="text-red-500 hover:text-red-700"><X className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-2 items-center pt-1 text-xs">
              <input
                type="text"
                placeholder="Nome do aluno avulso"
                value={inp.aluno_nome || ''}
                onChange={e => setPartInputs({ ...partInputs, [ws.id]: { ...inp, aluno_nome: e.target.value } })}
                className="px-3 py-1.5 border rounded-lg flex-1 min-w-[160px]"
              />
              <input
                type="number"
                step="0.01"
                placeholder="Valor (R$)"
                value={inp.valor_pago || ''}
                onChange={e => setPartInputs({ ...partInputs, [ws.id]: { ...inp, valor_pago: e.target.value } })}
                className="px-3 py-1.5 border rounded-lg w-28"
              />
              <select
                value={inp.forma_pagamento || 'PIX'}
                onChange={e => setPartInputs({ ...partInputs, [ws.id]: { ...inp, forma_pagamento: e.target.value } })}
                className="px-2.5 py-1.5 border rounded-lg bg-white"
              >
                {FORMAS_PAGAMENTO.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
              <button type="button" onClick={() => handleAddParticipant(ws.id)} className="px-3 py-1.5 bg-slate-800 text-white rounded-lg font-semibold">
                + Avulso
              </button>
            </div>
          </div>
        );
      })}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl">
            <h3 className="font-bold text-slate-800 mb-3">Novo Workshop — Ateliê Parceria</h3>
            <form onSubmit={handleCreateWorkshop} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Título</label>
                <input type="text" required value={wsForm.titulo} onChange={e => setWsForm({ ...wsForm, titulo: e.target.value })} placeholder="Ex: Oficina de Esmaltação em Cerâmica" className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Modalidade</label>
                  <input type="text" required value={wsForm.modalidade} onChange={e => setWsForm({ ...wsForm, modalidade: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Data</label>
                  <input type="date" required value={wsForm.data_realizacao} onChange={e => setWsForm({ ...wsForm, data_realizacao: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Professora Parceira</label>
                  <input type="text" required value={wsForm.professora_parceira} onChange={e => setWsForm({ ...wsForm, professora_parceira: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">Despesas Materiais (R$)</label>
                  <input type="number" step="0.01" min="0" value={wsForm.despesas_materiais} onChange={e => setWsForm({ ...wsForm, despesas_materiais: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
                </div>
              </div>
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Vincular a Curso (opcional)</label>
                <select value={wsForm.curso_id} onChange={e => setWsForm({ ...wsForm, curso_id: e.target.value })} className="w-full px-3 py-2 border rounded-lg bg-white">
                  <option value="">Centro Geral: Ateliê - Parceria</option>
                  {courses.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
                <button type="submit" className="px-4 py-2 bg-amber-700 text-white rounded-lg font-semibold">Criar Sessão</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
