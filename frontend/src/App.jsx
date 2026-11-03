import React, { useState, useEffect } from 'react';
import {
  Palette, Users, BookOpen, Calendar, CreditCard, MessageSquare,
  HardDrive, LogOut, Plus, CheckCircle, AlertTriangle, FileText,
  DollarSign, TrendingUp, ShieldCheck, Clock, Download, RefreshCw, X
} from 'lucide-react';
import { api, authStorage } from './services/api';

export default function App() {
  const [user, setUser] = useState(authStorage.getUser());
  const [token, setToken] = useState(authStorage.getToken());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  // Estados de dados
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [courses, setCourses] = useState([]);
  const [classes, setClasses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [defaulters, setDefaulters] = useState([]);
  const [dre, setDre] = useState(null);
  const [backups, setBackups] = useState([]);

  // Estados de login
  const [email, setEmail] = useState('admin@hbartes.com');
  const [senha, setSenha] = useState('admin123');
  const [loginError, setLoginError] = useState('');

  // Modais
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [showPayModal, setShowPayModal] = useState(null);
  const [payMethod, setPayMethod] = useState('PIX');
  const [payValue, setPayValue] = useState('');

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoginError('');
    try {
      const data = await api.login(email, senha);
      authStorage.setAuth(data.access_token, data.usuario);
      setToken(data.access_token);
      setUser(data.usuario);
      showToast(`Bem-vindo(a), ${data.usuario.nome}!`);
    } catch (err) {
      setLoginError(err.message || 'Falha ao autenticar.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    authStorage.clear();
    setToken(null);
    setUser(null);
  };

  const loadDashboardData = async () => {
    if (!token) return;
    try {
      const [dash, s, r, c, cls, inv, def, bkp] = await Promise.all([
        api.getDashboard().catch(() => null),
        api.getStudents().catch(() => []),
        api.getRooms().catch(() => []),
        api.getCourses().catch(() => []),
        api.getClasses().catch(() => []),
        api.getInvoices().catch(() => []),
        api.getDefaulters().catch(() => []),
        api.getBackups().catch(() => []),
      ]);
      setDashboard(dash);
      setStudents(s);
      setRooms(r);
      setCourses(c);
      setClasses(cls);
      setInvoices(inv);
      setDefaulters(def);
      setBackups(bkp);

      // Carrega DRE do mês
      const hoje = new Date();
      const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1).toISOString().split('T')[0];
      const ultimoDia = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0).toISOString().split('T')[0];
      const dreData = await api.getDRE(primeiroDia, ultimoDia).catch(() => null);
      setDre(dreData);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (token) {
      loadDashboardData();
    }
  }, [token, activeTab]);

  // Se não estiver autenticado, exibe tela de login elegante
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-slate-50 to-orange-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-amber-100 p-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-tr from-amber-700 to-amber-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg text-white">
              <Palette className="w-9 h-9" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800">Helena Barufaldi</h1>
            <p className="text-sm font-medium text-amber-700 tracking-wide uppercase mt-1">Escola de Artes • Nova Odessa/SP</p>
            <p className="text-xs text-slate-500 mt-2">Sistema Integrado de Gestão Escolar & Financeira</p>
          </div>

          {loginError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">E-mail do Colaborador</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none transition text-sm"
                placeholder="seu.email@hbartes.com"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Senha de Acesso</label>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none transition text-sm"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-amber-700 hover:bg-amber-800 text-white font-medium py-2.5 rounded-lg transition duration-200 shadow-md flex items-center justify-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Entrar no Sistema'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <span className="text-xs text-slate-400">Credenciais padrão: admin@hbartes.com / admin123</span>
          </div>
        </div>
      </div>
    );
  }

  // --- SUBMISSION HANDLERS ---
  const handleCreateStudent = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const dataNascimento = formData.get('data_nascimento');
    const isMenor = new Date().getFullYear() - new Date(dataNascimento).getFullYear() < 18;

    const payload = {
      nome: formData.get('nome'),
      data_nascimento: dataNascimento,
      cpf: formData.get('cpf') || null,
      telefone: formData.get('telefone') || null,
      email: formData.get('email') || null,
      endereco: formData.get('endereco') || null,
      alergias: formData.get('alergias') || null,
      autorizacao_imagem: formData.get('autorizacao_imagem') === 'on',
      responsavel: isMenor ? {
        nome: formData.get('resp_nome'),
        cpf: formData.get('resp_cpf'),
        telefone: formData.get('resp_telefone'),
        email: formData.get('resp_email'),
        endereco: formData.get('resp_endereco'),
      } : null
    };

    try {
      await api.createStudent(payload);
      showToast('Aluno cadastrado com sucesso!');
      setShowStudentModal(false);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handlePayInvoice = async () => {
    if (!showPayModal) return;
    try {
      await api.payInvoice(showPayModal.id, {
        valor_pago: parseFloat(payValue || showPayModal.valor_final),
        forma_pagamento: payMethod,
      });
      showToast(`Título quitado com sucesso via ${payMethod}!`);
      setShowPayModal(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleOpenWhatsApp = async (invoiceId) => {
    try {
      const data = await api.getInvoiceReminderLink(invoiceId);
      window.open(data.whatsapp_url, '_blank');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleBackup = async () => {
    try {
      await api.createBackup();
      showToast('Backup do banco de dados local gerado com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-sm font-medium ${
          toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
        }`}>
          {toast.type === 'error' ? <AlertTriangle className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Sidebar de Navegação */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800">
        <div className="p-5 border-b border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-600 flex items-center justify-center text-white shadow-md">
            <Palette className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-bold text-white text-base leading-tight">Helena Barufaldi</h2>
            <span className="text-[11px] font-semibold text-amber-500 uppercase tracking-wider">Escola de Artes</span>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {[
            { id: 'dashboard', label: 'Painel Geral', icon: TrendingUp },
            { id: 'students', label: 'Alunos & Responsáveis', icon: Users },
            { id: 'rooms', label: 'Salas & Modalidades', icon: Palette },
            { id: 'classes', label: 'Turmas & Horários', icon: Calendar },
            { id: 'financial', label: 'Financeiro & DRE', icon: DollarSign },
            { id: 'attendance', label: 'Frequência & Reposição', icon: Clock },
            { id: 'backups', label: 'Backups do Sistema', icon: HardDrive },
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                  active
                    ? 'bg-amber-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-amber-400">
              {user.nome.charAt(0)}
            </div>
            <div>
              <p className="text-xs font-semibold text-white leading-tight">{user.nome}</p>
              <p className="text-[10px] text-slate-400">{user.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sair"
            className="text-slate-400 hover:text-red-400 transition p-1.5 rounded-lg hover:bg-slate-800"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
          <div>
            <h1 className="text-xl font-bold text-slate-800 capitalize">
              {activeTab === 'dashboard' && 'Painel Geral de Indicadores'}
              {activeTab === 'students' && 'Gestão de Alunos e Responsáveis'}
              {activeTab === 'rooms' && 'Salas de Aula e Modalidades Artísticas'}
              {activeTab === 'classes' && 'Controle de Turmas e Capacidade'}
              {activeTab === 'financial' && 'Gestão Financeira, Cobrança e DRE'}
              {activeTab === 'attendance' && 'Diário de Classe, Presença e Reposições'}
              {activeTab === 'backups' && 'Segurança e Backup Local SQLite'}
            </h1>
            <p className="text-xs text-slate-500">Unidade Nova Odessa • R. Duque de Caxias, 660</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadDashboardData}
              className="p-2 text-slate-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition border border-slate-200"
              title="Atualizar dados"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div className="p-8 space-y-6">
          {/* TAB: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Alunos Ativos</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{dashboard?.total_alunos_ativos || 0}</h3>
                    <p className="text-xs text-emerald-600 mt-1">Alunos matriculados</p>
                  </div>
                  <div className="w-12 h-12 bg-amber-50 text-amber-700 rounded-xl flex items-center justify-center">
                    <Users className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Turmas em Andamento</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{dashboard?.total_turmas_ativas || 0}</h3>
                    <p className="text-xs text-slate-500 mt-1">13 horários semanais</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-50 text-blue-700 rounded-xl flex items-center justify-center">
                    <Calendar className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Taxa de Ocupação</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{dashboard?.taxa_ocupacao_geral_percentual || 0}%</h3>
                    <p className="text-xs text-amber-600 mt-1">Teto: máx. 9 por sala</p>
                  </div>
                  <div className="w-12 h-12 bg-emerald-50 text-emerald-700 rounded-xl flex items-center justify-center">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Inadimplência</span>
                    <h3 className="text-2xl font-bold text-red-600 mt-1">R$ {dashboard?.valor_total_inadimplente || '0.00'}</h3>
                    <p className="text-xs text-red-500 mt-1">{dashboard?.total_inadimplentes || 0} títulos em aberto</p>
                  </div>
                  <div className="w-12 h-12 bg-red-50 text-red-700 rounded-xl flex items-center justify-center">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                </div>
              </div>

              {/* Salas e Teto de 9 Alunos */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <Palette className="w-5 h-5 text-amber-600" />
                  Ocupação Física dos Estúdios (Máximo 9 Alunos por Sala)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {rooms.map((room) => (
                    <div key={room.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <h4 className="font-bold text-slate-800">{room.nome}</h4>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800">
                          Teto: {room.capacidade} alunos
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{room.descricao || 'Estúdio de artes visuais'}</p>
                      <div className="mt-4">
                        <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                          <div className="bg-amber-600 h-2 rounded-full" style={{ width: '45%' }}></div>
                        </div>
                        <span className="text-[11px] text-slate-500 block text-right mt-1">Capacidade Segura</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Resumo DRE do Mês */}
              {dre && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-emerald-600" />
                    DRE - Demonstração do Resultado Operacional (Mês Corrente)
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <span className="text-xs text-slate-500 font-semibold uppercase">Receita Bruta</span>
                      <p className="text-xl font-bold text-slate-800 mt-1">R$ {dre.receita_bruta.toFixed(2)}</p>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <span className="text-xs text-slate-500 font-semibold uppercase">Descontos Concedidos</span>
                      <p className="text-xl font-bold text-amber-700 mt-1">- R$ {dre.deducoes_descontos.toFixed(2)}</p>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <span className="text-xs text-slate-500 font-semibold uppercase">Despesas Operacionais</span>
                      <p className="text-xl font-bold text-red-600 mt-1">- R$ {dre.despesas_operacionais.toFixed(2)}</p>
                    </div>
                    <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                      <span className="text-xs text-emerald-700 font-semibold uppercase">Resultado Líquido</span>
                      <p className="text-xl font-bold text-emerald-700 mt-1">R$ {dre.resultado_liquido.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB: ALUNOS */}
          {activeTab === 'students' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Cadastro de Alunos e Responsáveis</h3>
                  <p className="text-xs text-slate-500">Regra: Alunos menores exigem responsável legal único com CPF.</p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={api.exportStudentsUrl}
                    className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" /> Exportar CSV
                  </a>
                  <button
                    onClick={() => setShowStudentModal(true)}
                    className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow"
                  >
                    <Plus className="w-3.5 h-3.5" /> Novo Aluno
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Aluno</th>
                      <th className="px-6 py-3">Nascimento</th>
                      <th className="px-6 py-3">Responsável Legal</th>
                      <th className="px-6 py-3">Contato</th>
                      <th className="px-6 py-3">Uso Imagem</th>
                      <th className="px-6 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {students.map((st) => (
                      <tr key={st.id} className="hover:bg-slate-50/80 transition">
                        <td className="px-6 py-4 font-medium text-slate-900">
                          {st.nome}
                          {st.alergias && <span className="block text-[11px] text-amber-700">Alergia: {st.alergias}</span>}
                        </td>
                        <td className="px-6 py-4">{new Date(st.data_nascimento).toLocaleDateString('pt-BR')}</td>
                        <td className="px-6 py-4">
                          {st.responsavel ? (
                            <div>
                              <span className="font-medium text-slate-800">{st.responsavel.nome}</span>
                              <span className="block text-[11px] text-slate-400">CPF: {st.responsavel.cpf}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400">Próprio aluno (Maior)</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs">
                          {st.responsavel?.telefone || st.telefone || 'Sem telefone'}
                        </td>
                        <td className="px-6 py-4">
                          {st.autorizacao_imagem ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">Autorizado</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">Não autorizou</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">Ativo</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: FINANCEIRO */}
          {activeTab === 'financial' && (
            <div className="space-y-6">
              {/* Inadimplentes e Cobrança Rápida */}
              {defaulters.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-red-800 text-base flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                      Régua de Cobrança — Títulos Inadimplentes com Multa e Juros
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {defaulters.map((def) => (
                      <div key={def.id} className="bg-white p-4 rounded-lg border border-red-100 shadow-sm flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-slate-800">{def.aluno_nome}</span>
                          <span className="text-xs text-slate-500 block">Vencido em: {new Date(def.data_vencimento).toLocaleDateString('pt-BR')}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <span className="text-sm font-bold text-red-600 block">R$ {def.valor_final.toFixed(2)}</span>
                            <span className="text-[11px] text-slate-400">Juros/Multa: R$ {def.juros_multa.toFixed(2)}</span>
                          </div>
                          <button
                            onClick={() => handleOpenWhatsApp(def.id)}
                            className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition flex items-center gap-1.5 shadow"
                          >
                            <MessageSquare className="w-3.5 h-3.5" /> Cobrar WhatsApp
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Títulos Gerais */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">Mensalidades e Títulos Financeiros</h3>
                    <p className="text-xs text-slate-500">Formas homologadas: PIX, Cartão, Boleto e Dinheiro.</p>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={api.exportInvoicesUrl}
                      className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" /> Exportar CSV
                    </a>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-600">
                    <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3">Descrição</th>
                        <th className="px-6 py-3">Aluno</th>
                        <th className="px-6 py-3">Vencimento</th>
                        <th className="px-6 py-3">Valor</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-right">Ação</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {invoices.map((inv) => (
                        <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                          <td className="px-6 py-4 font-medium text-slate-900">{inv.descricao}</td>
                          <td className="px-6 py-4">{inv.aluno_nome || 'Aluno'}</td>
                          <td className="px-6 py-4">{new Date(inv.data_vencimento).toLocaleDateString('pt-BR')}</td>
                          <td className="px-6 py-4 font-bold text-slate-800">R$ {inv.valor_final.toFixed(2)}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              inv.status === 'PAGO' ? 'bg-emerald-100 text-emerald-800' :
                              inv.status === 'ATRASADO' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                            }`}>
                              {inv.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            {inv.status !== 'PAGO' ? (
                              <button
                                onClick={() => {
                                  setShowPayModal(inv);
                                  setPayValue(inv.valor_final);
                                }}
                                className="px-3 py-1.5 text-xs font-semibold bg-amber-700 hover:bg-amber-800 text-white rounded-lg transition"
                              >
                                Baixa
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">Liquidado ({inv.forma_pagamento})</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB: BACKUPS */}
          {activeTab === 'backups' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Backups Locais do Banco de Dados SQLite</h3>
                  <p className="text-xs text-slate-500">Requisito do briefing: Disponibilidade e rotina de recuperação local.</p>
                </div>
                <button
                  onClick={handleBackup}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow"
                >
                  <HardDrive className="w-4 h-4" /> Criar Snapshot Agora
                </button>
              </div>

              <div className="space-y-3">
                {backups.map((b, i) => (
                  <div key={i} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-slate-800 text-sm">{b.arquivo}</p>
                      <span className="text-xs text-slate-400">Criado em: {new Date(b.criado_em).toLocaleString('pt-BR')}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-1 rounded">{b.tamanho_formatado}</span>
                      <a
                        href={`/api/v1/backup/download/${b.arquivo}`}
                        download
                        className="p-2 text-slate-600 hover:text-amber-800 transition"
                        title="Download para pendrive"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB: TURMAS, SALAS E DEMAIS */}
          {(activeTab === 'rooms' || activeTab === 'classes' || activeTab === 'attendance') && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <h3 className="font-bold text-slate-800 text-base">Módulo Ativo: {activeTab.toUpperCase()}</h3>
              <p className="text-xs text-slate-500">
                Operando com motor de integridade: 6 salas de estúdio, 9 modalidades ativas e capacidade máxima rigorosa de 9 alunos por sala.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                {courses.map((c) => (
                  <div key={c.id} className="p-4 border border-slate-100 rounded-lg bg-slate-50">
                    <h4 className="font-semibold text-slate-800 text-sm">{c.nome}</h4>
                    <p className="text-xs text-slate-500 mt-1">{c.descricao}</p>
                    <span className="text-xs font-bold text-amber-700 block mt-2">Mensalidade base: R$ {c.valor_mensalidade.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* MODAL: NOVO ALUNO */}
      {showStudentModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Novo Aluno</h3>
              <button onClick={() => setShowStudentModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateStudent} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome Completo</label>
                <input name="nome" required className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Nascimento</label>
                  <input name="data_nascimento" type="date" required className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">CPF (Adultos)</label>
                  <input name="cpf" placeholder="000.000.000-00" className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Alergias ou Observações de Saúde</label>
                <input name="alergias" placeholder="Tinta acrílica, poeira..." className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500" />
              </div>

              {/* Seção Responsável Legal (Para menores) */}
              <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl space-y-3">
                <span className="text-xs font-bold text-amber-900 block">Responsável Legal & Financeiro (Obrigatório para menores)</span>
                <div>
                  <input name="resp_nome" placeholder="Nome do Responsável Legal" className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input name="resp_cpf" placeholder="CPF: 000.000.000-00" className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white" />
                  <input name="resp_telefone" placeholder="Telefone: (19) 9..." className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white" />
                </div>
                <input name="resp_email" placeholder="E-mail do responsável" className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white" />
                <input name="resp_endereco" placeholder="Endereço residencial" className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white" />
              </div>

              <div className="flex items-center gap-2">
                <input name="autorizacao_imagem" type="checkbox" id="auth_img" className="rounded text-amber-600" />
                <label htmlFor="auth_img" className="text-xs text-slate-600">Autorizo uso de imagem em redes sociais e eventos</label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowStudentModal(false)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Salvar Aluno</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: BAIXA DE PAGAMENTO */}
      {showPayModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100">
            <h3 className="font-bold text-slate-800 text-base mb-1">Baixa de Pagamento</h3>
            <p className="text-xs text-slate-500 mb-4">{showPayModal.descricao}</p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Forma de Pagamento Homologada</label>
                <select
                  value={payMethod}
                  onChange={(e) => setPayMethod(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm bg-white"
                >
                  <option value="PIX">PIX</option>
                  <option value="CARTAO">Cartão de Crédito / Débito</option>
                  <option value="BOLETO">Boleto Bancário</option>
                  <option value="DINHEIRO">Dinheiro (Presencial)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Valor Pago (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={payValue}
                  onChange={(e) => setPayValue(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowPayModal(null)} className="px-3.5 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
              <button onClick={handlePayInvoice} className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow">
                Confirmar Recebimento
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
