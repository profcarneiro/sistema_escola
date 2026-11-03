import React, { useState, useEffect } from 'react';
import {
  Palette, Users, BookOpen, Calendar, CreditCard, MessageSquare,
  HardDrive, LogOut, Plus, CheckCircle, AlertTriangle, FileText,
  DollarSign, TrendingUp, ShieldCheck, Clock, Download, RefreshCw, X,
  GraduationCap, Check, UserPlus
} from 'lucide-react';
import { api, authStorage } from './services/api';

export default function App() {
  const [user, setUser] = useState(authStorage.getUser());
  const [token, setToken] = useState(authStorage.getToken());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  // Estados de dados principais
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [courses, setCourses] = useState([]);
  const [teachers, setTeachers] = useState([]);
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
  const [showCourseModal, setShowCourseModal] = useState(false);
  const [showEnrollmentModal, setShowEnrollmentModal] = useState(false);
  const [preselectedStudentId, setPreselectedStudentId] = useState(null);
  const [showClassModal, setShowClassModal] = useState(false);
  const [showPayModal, setShowPayModal] = useState(null);
  const [payMethod, setPayMethod] = useState('PIX');
  const [payValue, setPayValue] = useState('');

  // Estados para Frequência / Diário
  const [selectedClassForAttendance, setSelectedClassForAttendance] = useState('');
  const [attendanceDate, setAttendanceDate] = useState(new Date().toISOString().split('T')[0]);
  const [lessonTopic, setLessonTopic] = useState('');
  const [lessonContent, setLessonContent] = useState('');
  const [lessonMaterials, setLessonMaterials] = useState('');
  const [attendanceRecords, setAttendanceRecords] = useState({});
  const [classLessonsHistory, setClassLessonsHistory] = useState([]);

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
      const [dash, s, r, c, t, cls, enr, inv, def, bkp] = await Promise.all([
        api.getDashboard().catch(() => null),
        api.getStudents().catch(() => []),
        api.getRooms().catch(() => []),
        api.getCourses().catch(() => []),
        api.getTeachers().catch(() => []),
        api.getClasses().catch(() => []),
        api.getEnrollments().catch(() => []),
        api.getInvoices().catch(() => []),
        api.getDefaulters().catch(() => []),
        api.getBackups().catch(() => []),
      ]);
      setDashboard(dash);
      setStudents(s);
      setRooms(r);
      setCourses(c);
      setTeachers(t);
      setClasses(cls);
      setEnrollments(enr);
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

  // Se trocar a turma na frequência, carrega o histórico de aulas
  useEffect(() => {
    if (selectedClassForAttendance) {
      api.getLessons(selectedClassForAttendance)
        .then((data) => setClassLessonsHistory(data))
        .catch(() => setClassLessonsHistory([]));
      
      // Inicializa presença de todos os matriculados como PRESENTE
      const turmEnr = enrollments.filter(e => e.turma_id === parseInt(selectedClassForAttendance) && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
      const initialAttendance = {};
      turmEnr.forEach(e => {
        initialAttendance[e.aluno_id] = 'PRESENTE';
      });
      setAttendanceRecords(initialAttendance);
    } else {
      setClassLessonsHistory([]);
      setAttendanceRecords({});
    }
  }, [selectedClassForAttendance, enrollments]);

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

  // 1. Cadastrar Aluno
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

  // 2. Cadastrar Curso / Modalidade Artística
  const handleCreateCourse = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = {
      nome: formData.get('nome'),
      descricao: formData.get('descricao') || null,
      duracao_meses: parseInt(formData.get('duracao_meses') || '12'),
      valor_mensalidade: parseFloat(formData.get('valor_mensalidade') || '0'),
    };

    try {
      await api.createCourse(payload);
      showToast('Modalidade artística cadastrada com sucesso!');
      setShowCourseModal(false);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 3. Matricular Aluno em Turma/Curso
  const handleCreateEnrollment = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const descTipo = formData.get('tipo_desconto');
    const payload = {
      aluno_id: parseInt(formData.get('aluno_id')),
      turma_id: parseInt(formData.get('turma_id')),
      data_matricula: formData.get('data_matricula'),
      data_inicio: formData.get('data_inicio'),
      data_termino_previsto: formData.get('data_termino_previsto') || null,
      valor_mensalidade: parseFloat(formData.get('valor_mensalidade') || '0'),
      desconto_percentual: parseFloat(formData.get('desconto_percentual') || '0'),
      tipo_desconto: descTipo && descTipo !== 'nenhum' ? descTipo : null,
      aula_experimental: formData.get('aula_experimental') === 'on',
      observacoes: formData.get('observacoes') || null,
    };

    try {
      await api.createEnrollment(payload);
      showToast('Aluno matriculado com sucesso no curso!');
      setShowEnrollmentModal(false);
      setPreselectedStudentId(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 4. Cadastrar Turma
  const handleCreateClass = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = {
      nome: formData.get('nome'),
      curso_id: parseInt(formData.get('curso_id')),
      sala_id: parseInt(formData.get('sala_id')),
      professor_id: parseInt(formData.get('professor_id')),
      faixa_etaria: formData.get('faixa_etaria'),
      dia_semana: formData.get('dia_semana'),
      turno: formData.get('turno'),
      horario_inicio: formData.get('horario_inicio'),
      horario_fim: formData.get('horario_fim'),
      capacidade_maxima: 9
    };

    try {
      await api.createClass(payload);
      showToast('Turma criada com sucesso!');
      setShowClassModal(false);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 5. Salvar Diário de Classe e Frequência
  const handleSaveAttendance = async (e) => {
    e.preventDefault();
    if (!selectedClassForAttendance) {
      showToast('Selecione uma turma para lançar a frequência.', 'error');
      return;
    }

    const turmaObj = classes.find(c => c.id === parseInt(selectedClassForAttendance));
    if (!turmaObj) return;

    try {
      // 1. Cria a lição no diário
      const lesson = await api.createLesson({
        turma_id: turmaObj.id,
        professor_id: turmaObj.professor_id,
        data_aula: attendanceDate,
        tema_aula: lessonTopic || 'Aula Regular',
        conteudo_programatico: lessonContent || null,
        materiais_utilizados: lessonMaterials || null,
        observacoes: null
      });

      // 2. Registra o lote de chamada
      const turmEnr = enrollments.filter(e => e.turma_id === turmaObj.id && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
      const frequencias = turmEnr.map(e => ({
        aluno_id: e.aluno_id,
        matricula_id: e.id,
        status: attendanceRecords[e.aluno_id] || 'PRESENTE',
        motivo_justificativa: null
      }));

      if (frequencias.length > 0) {
        await api.recordAttendance(lesson.id, frequencias);
      }

      showToast('Diário de classe e chamada salvos com sucesso!');
      setLessonTopic('');
      setLessonContent('');
      setLessonMaterials('');

      // Recarrega histórico
      const updatedLessons = await api.getLessons(turmaObj.id);
      setClassLessonsHistory(updatedLessons);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 6. Quitar Mensalidade
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

  // 7. WhatsApp Boas-Vindas
  const handleSendWelcomeWhatsApp = async (matriculaId) => {
    try {
      const data = await api.getEnrollmentWelcomeLink(matriculaId);
      window.open(data.whatsapp_url, '_blank');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 8. WhatsApp Cobrança
  const handleOpenWhatsApp = async (invoiceId) => {
    try {
      const data = await api.getInvoiceReminderLink(invoiceId);
      window.open(data.whatsapp_url, '_blank');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 9. Criar Backup
  const handleBackup = async () => {
    try {
      await api.createBackup();
      showToast('Backup do banco de dados local gerado com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Utilitários de busca de dados relacionados
  const getStudentEnrollments = (studentId) => {
    return enrollments.filter(e => e.aluno_id === studentId && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
  };

  const getTurmaStudents = (turmaId) => {
    const enrs = enrollments.filter(e => e.turma_id === turmaId && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
    return enrs.map(e => e.aluno_nome || `Aluno #${e.aluno_id}`);
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
            { id: 'courses', label: 'Cursos & Modalidades', icon: BookOpen },
            { id: 'enrollments', label: 'Matrículas & Contratos', icon: GraduationCap },
            { id: 'classes', label: 'Turmas & Horários', icon: Calendar },
            { id: 'rooms', label: 'Salas & Capacidade (9)', icon: Palette },
            { id: 'financial', label: 'Financeiro & DRE', icon: DollarSign },
            { id: 'attendance', label: 'Frequência & Diário', icon: Clock },
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
            <h1 className="text-xl font-bold text-slate-800">
              {activeTab === 'dashboard' && 'Painel Geral de Indicadores'}
              {activeTab === 'students' && 'Gestão de Alunos e Responsáveis'}
              {activeTab === 'courses' && 'Catálogo de Cursos & Modalidades Artísticas'}
              {activeTab === 'enrollments' && 'Matrículas de Alunos e Vínculos com Turmas'}
              {activeTab === 'classes' && 'Controle de Turmas e Capacidade Máxima'}
              {activeTab === 'rooms' && 'Estúdios Físicos (Teto de 9 Alunos)'}
              {activeTab === 'financial' && 'Gestão Financeira, Cobrança e DRE'}
              {activeTab === 'attendance' && 'Diário de Classe, Presença e Frequência'}
              {activeTab === 'backups' && 'Segurança e Backup Local SQLite'}
            </h1>
            <p className="text-xs text-slate-500">Unidade Nova Odessa/SP • Porta 8080 • Servidor Local Seguro</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadDashboardData}
              className="p-2 text-slate-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition border border-slate-200 flex items-center gap-1.5 text-xs font-semibold"
              title="Atualizar dados"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Atualizar
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div className="p-8 space-y-6">

          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Alunos Ativos</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{dashboard?.total_alunos_ativos || students.length}</h3>
                    <p className="text-xs text-emerald-600 mt-1">{enrollments.filter(e => e.status === 'ATIVA').length} matrículas ativas</p>
                  </div>
                  <div className="w-12 h-12 bg-amber-50 text-amber-700 rounded-xl flex items-center justify-center">
                    <Users className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">Modalidades Ativas</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{courses.length}</h3>
                    <p className="text-xs text-slate-500 mt-1">{classes.length} turmas cadastradas</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-50 text-blue-700 rounded-xl flex items-center justify-center">
                    <BookOpen className="w-6 h-6" />
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
                    <p className="text-xs text-red-500 mt-1">{defaulters.length} títulos em aberto</p>
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
                  Ocupação dos Estúdios Físicos (Máximo Rigoroso de 9 Alunos por Sala)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {rooms.map((room) => {
                    const roomClasses = classes.filter(c => c.sala_id === room.id);
                    return (
                      <div key={room.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-col justify-between">
                        <div className="flex justify-between items-start">
                          <h4 className="font-bold text-slate-800">{room.nome}</h4>
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800">
                            Teto: {room.capacidade} alunos
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">{room.descricao || 'Estúdio de artes visuais'}</p>
                        <div className="mt-4 pt-3 border-t border-slate-200/60">
                          <div className="flex justify-between text-xs text-slate-600 mb-1">
                            <span>Turmas no estúdio:</span>
                            <span className="font-bold">{roomClasses.length} turmas</span>
                          </div>
                          <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-amber-600 h-2 rounded-full"
                              style={{ width: `${Math.min(100, (roomClasses.length / 3) * 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
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

          {/* TAB 2: ALUNOS & RESPONSÁVEIS */}
          {activeTab === 'students' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Cadastro de Alunos e Cursos Matriculados</h3>
                  <p className="text-xs text-slate-500">Regra: Alunos menores exigem responsável legal único. Vincule cursos diretamente no botão "+ Matricular".</p>
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
                      <th className="px-6 py-3">Cursos Vinculados</th>
                      <th className="px-6 py-3">Responsável Legal</th>
                      <th className="px-6 py-3">Contato</th>
                      <th className="px-6 py-3">Imagem</th>
                      <th className="px-6 py-3 text-right">Ação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {students.map((st) => {
                      const stEnrs = getStudentEnrollments(st.id);
                      return (
                        <tr key={st.id} className="hover:bg-slate-50/80 transition">
                          <td className="px-6 py-4 font-medium text-slate-900">
                            <div>{st.nome}</div>
                            <span className="text-[11px] text-slate-400">
                              Nasc: {new Date(st.data_nascimento).toLocaleDateString('pt-BR')}
                            </span>
                            {st.alergias && <span className="block text-[11px] text-amber-700">Alergia: {st.alergias}</span>}
                          </td>
                          <td className="px-6 py-4">
                            {stEnrs.length > 0 ? (
                              <div className="flex flex-wrap gap-1.5">
                                {stEnrs.map((e) => (
                                  <span key={e.id} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-100 text-amber-900 border border-amber-200">
                                    <BookOpen className="w-3 h-3 text-amber-700" />
                                    {e.turma_nome || `Turma #${e.turma_id}`}
                                    {e.aula_experimental && <span className="text-[9px] bg-amber-300 text-amber-900 px-1 rounded ml-1">Exp.</span>}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-slate-400 italic">Sem curso vinculado</span>
                            )}
                          </td>
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
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => {
                                setPreselectedStudentId(st.id);
                                setShowEnrollmentModal(true);
                              }}
                              className="px-3 py-1.5 text-xs font-semibold bg-amber-700 hover:bg-amber-800 text-white rounded-lg transition inline-flex items-center gap-1 shadow-sm"
                              title="Matricular este aluno em uma modalidade/turma"
                            >
                              <Plus className="w-3.5 h-3.5" /> Matricular
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: CURSOS & MODALIDADES ARTÍSTICAS */}
          {activeTab === 'courses' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Catálogo de Modalidades de Arte</h3>
                  <p className="text-xs text-slate-500">Cadastre novas técnicas artísticas e defina o valor base da mensalidade.</p>
                </div>
                <button
                  onClick={() => setShowCourseModal(true)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow"
                >
                  <Plus className="w-3.5 h-3.5" /> Novo Curso / Modalidade
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {courses.map((course) => {
                  const courseClasses = classes.filter(c => c.curso_id === course.id);
                  const enrolledCount = enrollments.filter(e => {
                    const t = classes.find(c => c.id === e.turma_id);
                    return t && t.curso_id === course.id && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL');
                  }).length;

                  return (
                    <div key={course.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:border-amber-400 transition">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
                            <BookOpen className="w-4 h-4" />
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                            Ativo
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-slate-800 mt-3">{course.nome}</h4>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-3">
                          {course.descricao || 'Modalidade prática com foco no desenvolvimento técnico e expressivo.'}
                        </p>
                      </div>

                      <div className="mt-5 pt-4 border-t border-slate-100 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Duração estimada:</span>
                          <span className="font-semibold text-slate-700">{course.duracao_meses} meses</span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-500">Turmas / Alunos:</span>
                          <span className="font-semibold text-slate-700">{courseClasses.length} turmas • {enrolledCount} alunos</span>
                        </div>
                        <div className="flex justify-between items-center pt-2">
                          <span className="text-xs font-semibold text-slate-500">Mensalidade base:</span>
                          <span className="text-base font-bold text-amber-800">R$ {course.valor_mensalidade.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 4: MATRÍCULAS & CONTRATOS */}
          {activeTab === 'enrollments' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Matrículas Ativas e Vínculos de Alunos</h3>
                  <p className="text-xs text-slate-500">Vínculo direto entre Aluno e Turma/Curso com contrato e controle de desconto.</p>
                </div>
                <button
                  onClick={() => {
                    setPreselectedStudentId(null);
                    setShowEnrollmentModal(true);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow"
                >
                  <Plus className="w-3.5 h-3.5" /> Nova Matrícula
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Contrato / Aluno</th>
                      <th className="px-6 py-3">Curso & Turma</th>
                      <th className="px-6 py-3">Início</th>
                      <th className="px-6 py-3">Mensalidade</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3 text-right">Comunicação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {enrollments.map((enr) => (
                      <tr key={enr.id} className="hover:bg-slate-50/80 transition">
                        <td className="px-6 py-4 font-medium text-slate-900">
                          <div>{enr.aluno_nome || `Aluno #${enr.aluno_id}`}</div>
                          <span className="text-[11px] text-slate-400">{enr.numero_contrato || 'Contrato pendente'}</span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="font-semibold text-slate-800 block">{enr.turma_nome || `Turma #${enr.turma_id}`}</span>
                          {enr.aula_experimental && (
                            <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">Aula Experimental</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs">
                          {new Date(enr.data_inicio).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-6 py-4">
                          <span className="font-bold text-slate-800 block">
                            R$ {(enr.valor_com_desconto || enr.valor_mensalidade).toFixed(2)}
                          </span>
                          {enr.desconto_percentual > 0 && (
                            <span className="text-[11px] text-emerald-600">
                              {enr.desconto_percentual}% off ({enr.tipo_desconto})
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            enr.status === 'ATIVA' ? 'bg-emerald-100 text-emerald-800' :
                            enr.status === 'EXPERIMENTAL' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {enr.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => handleSendWelcomeWhatsApp(enr.id)}
                            className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition inline-flex items-center gap-1 shadow-sm"
                            title="Enviar boas-vindas e detalhes da turma no WhatsApp"
                          >
                            <MessageSquare className="w-3.5 h-3.5" /> WhatsApp
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: TURMAS & HORÁRIOS */}
          {activeTab === 'classes' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Grade de Turmas e Horários Semanais</h3>
                  <p className="text-xs text-slate-500">Teto rigoroso de 9 alunos por turma. Validação automática contra choque de sala e professor.</p>
                </div>
                <button
                  onClick={() => setShowClassModal(true)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow"
                >
                  <Plus className="w-3.5 h-3.5" /> Nova Turma
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {classes.map((cls) => {
                  const enrolledNames = getTurmaStudents(cls.id);
                  const enrolledCount = enrolledNames.length;
                  const isFull = enrolledCount >= cls.capacidade_maxima;

                  return (
                    <div key={cls.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 hover:border-amber-400 transition">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wide">
                            {cls.dia_semana} • {cls.turno} ({cls.horario_inicio} às {cls.horario_fim})
                          </span>
                          <h4 className="text-base font-bold text-slate-800 mt-1">{cls.nome}</h4>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Curso: <span className="font-semibold text-slate-700">{cls.curso_nome || 'Artes'}</span> • Faixa: <span className="font-semibold text-slate-700">{cls.faixa_etaria}</span>
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          isFull ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                        }`}>
                          {enrolledCount} / {cls.capacidade_maxima} vagas
                        </span>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                        <span>Professor: <strong className="text-slate-700">{cls.professor_nome || 'Docente'}</strong></span>
                        <span>Sala: <strong className="text-slate-700">{cls.sala_nome || `Sala #${cls.sala_id}`}</strong></span>
                      </div>

                      <div className="mt-3">
                        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-2 rounded-full ${isFull ? 'bg-red-600' : 'bg-amber-600'}`}
                            style={{ width: `${(enrolledCount / cls.capacidade_maxima) * 100}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Lista de Alunos Matriculados */}
                      <div className="mt-4 pt-3 border-t border-slate-100">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide block mb-1">
                          Alunos Nesta Turma:
                        </span>
                        {enrolledNames.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {enrolledNames.map((name, idx) => (
                              <span key={idx} className="px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-700 font-medium">
                                {name}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Nenhum aluno matriculado nesta turma ainda.</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 6: SALAS & CAPACIDADE */}
          {activeTab === 'rooms' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                <h3 className="font-bold text-slate-800 text-lg">Estúdios de Criação e Salas de Aula</h3>
                <p className="text-xs text-slate-500">Infraestrutura física homologada com teto inegociável de 9 alunos por sala.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {rooms.map((room) => {
                  const roomClasses = classes.filter(c => c.sala_id === room.id);
                  return (
                    <div key={room.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
                            <Palette className="w-4 h-4" />
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">
                            Capacidade: {room.capacidade} alunos
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-slate-800 mt-3">{room.nome}</h4>
                        <p className="text-xs text-slate-500 mt-1">{room.descricao}</p>
                      </div>

                      <div className="mt-5 pt-4 border-t border-slate-100">
                        <span className="text-xs font-semibold text-slate-700 block mb-2">Turmas que usam esta sala:</span>
                        {roomClasses.length > 0 ? (
                          <div className="space-y-1">
                            {roomClasses.map(c => (
                              <div key={c.id} className="text-xs text-slate-600 bg-slate-50 p-1.5 rounded flex justify-between">
                                <span>{c.nome}</span>
                                <span className="font-semibold text-amber-800">{c.dia_semana}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Disponível em todos os horários.</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 7: FINANCEIRO & DRE */}
          {activeTab === 'financial' && (
            <div className="space-y-6">
              {/* Inadimplentes e Cobrança Rápida */}
              {defaulters.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-red-800 text-base flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                      Régua de Cobrança — Títulos Inadimplentes com Multa (2%) e Juros
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

          {/* TAB 8: FREQUÊNCIA & DIÁRIO DE CLASSE */}
          {activeTab === 'attendance' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                <h3 className="font-bold text-slate-800 text-lg">Diário de Classe & Chamada Semanal</h3>
                <p className="text-xs text-slate-500">Selecione uma turma para registrar o tema trabalhado e a presença dos alunos matriculados.</p>

                <form onSubmit={handleSaveAttendance} className="mt-6 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Selecione a Turma</label>
                      <select
                        value={selectedClassForAttendance}
                        onChange={(e) => setSelectedClassForAttendance(e.target.value)}
                        required
                        className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                      >
                        <option value="">-- Escolha uma turma ativa --</option>
                        {classes.map(c => (
                          <option key={c.id} value={c.id}>
                            {c.nome} ({c.dia_semana} • {c.horario_inicio}-{c.horario_fim})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Data da Aula</label>
                      <input
                        type="date"
                        value={attendanceDate}
                        onChange={(e) => setAttendanceDate(e.target.value)}
                        required
                        className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Tema da Aula / Assunto</label>
                      <input
                        type="text"
                        value={lessonTopic}
                        onChange={(e) => setLessonTopic(e.target.value)}
                        placeholder="Ex: Introdução a luz e sombra com grafite 6B"
                        required
                        className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Materiais Utilizados</label>
                      <input
                        type="text"
                        value={lessonMaterials}
                        onChange={(e) => setLessonMaterials(e.target.value)}
                        placeholder="Ex: Papel Canson 200g, carvão e esfuminho"
                        className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Conteúdo Programático e Observações</label>
                    <textarea
                      value={lessonContent}
                      onChange={(e) => setLessonContent(e.target.value)}
                      rows="2"
                      placeholder="Exercícios práticos desenvolvidos pelos alunos..."
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    ></textarea>
                  </div>

                  {/* Lista de Chamada Interativa */}
                  {selectedClassForAttendance && (
                    <div className="mt-6 pt-4 border-t border-slate-200">
                      <h4 className="font-bold text-slate-800 text-sm mb-3">
                        Lista de Chamada dos Alunos Matriculados:
                      </h4>

                      {enrollments.filter(e => e.turma_id === parseInt(selectedClassForAttendance) && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL')).length > 0 ? (
                        <div className="space-y-2">
                          {enrollments.filter(e => e.turma_id === parseInt(selectedClassForAttendance) && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL')).map((enr) => {
                            const currentStatus = attendanceRecords[enr.aluno_id] || 'PRESENTE';
                            return (
                              <div key={enr.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50">
                                <span className="font-medium text-slate-800 text-sm">{enr.aluno_nome}</span>
                                <div className="flex gap-2">
                                  {['PRESENTE', 'FALTA', 'JUSTIFICADA'].map(st => (
                                    <button
                                      type="button"
                                      key={st}
                                      onClick={() => setAttendanceRecords({ ...attendanceRecords, [enr.aluno_id]: st })}
                                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                                        currentStatus === st
                                          ? (st === 'PRESENTE' ? 'bg-emerald-600 text-white' : st === 'FALTA' ? 'bg-red-600 text-white' : 'bg-amber-600 text-white')
                                          : 'bg-white border text-slate-600 hover:bg-slate-100'
                                      }`}
                                    >
                                      {st}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-400 italic">Não há alunos matriculados nesta turma no momento.</p>
                      )}

                      <div className="flex justify-end mt-4">
                        <button
                          type="submit"
                          className="px-5 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow"
                        >
                          Salvar Diário e Frequência
                        </button>
                      </div>
                    </div>
                  )}
                </form>
              </div>

              {/* Histórico de Aulas */}
              {classLessonsHistory.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                  <h4 className="font-bold text-slate-800 text-sm mb-4">Aulas Registradas Anteriormente</h4>
                  <div className="space-y-3">
                    {classLessonsHistory.map(l => (
                      <div key={l.id} className="p-3 rounded-lg border border-slate-100 bg-slate-50 flex justify-between items-center text-xs">
                        <div>
                          <strong className="text-slate-800 block text-sm">{l.tema_aula}</strong>
                          <span className="text-slate-500">Data: {new Date(l.data_aula).toLocaleDateString('pt-BR')} • {l.materiais_utilizados || 'Sem materiais'}</span>
                        </div>
                        <span className="px-2 py-1 rounded bg-slate-200 text-slate-700 font-semibold">Registrada</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 9: BACKUPS */}
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

        </div>
      </main>

      {/* MODAL 1: NOVO ALUNO */}
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

      {/* MODAL 2: NOVO CURSO / MODALIDADE ARTÍSTICA */}
      {showCourseModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Nova Modalidade Artística</h3>
              <button onClick={() => setShowCourseModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateCourse} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome do Curso / Modalidade</label>
                <input
                  name="nome"
                  required
                  placeholder="Ex: Pintura a Óleo, Mangá Digital, Escultura..."
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Descrição e Técnicas</label>
                <textarea
                  name="descricao"
                  rows="3"
                  placeholder="Abordagem de materiais, exercícios práticos, histórico..."
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                ></textarea>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Duração (Meses)</label>
                  <input
                    name="duracao_meses"
                    type="number"
                    defaultValue="12"
                    min="1"
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Mensalidade Base (R$)</label>
                  <input
                    name="valor_mensalidade"
                    type="number"
                    step="0.01"
                    defaultValue="280.00"
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800 outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowCourseModal(false)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Cadastrar Curso</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: MATRICULAR ALUNO EM CURSO / TURMA */}
      {showEnrollmentModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Matricular Aluno em Curso / Turma</h3>
              <button onClick={() => setShowEnrollmentModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateEnrollment} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Selecione o Aluno</label>
                <select
                  name="aluno_id"
                  defaultValue={preselectedStudentId || ''}
                  required
                  className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                >
                  <option value="">-- Escolha um aluno --</option>
                  {students.map(s => (
                    <option key={s.id} value={s.id}>{s.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Selecione o Curso & Turma</label>
                <select
                  name="turma_id"
                  required
                  onChange={(e) => {
                    const selTurma = classes.find(c => c.id === parseInt(e.target.value));
                    if (selTurma) {
                      const selCourse = courses.find(cr => cr.id === selTurma.curso_id);
                      if (selCourse) {
                        const valInput = document.getElementById('enroll_valor_mensalidade');
                        if (valInput) valInput.value = selCourse.valor_mensalidade.toFixed(2);
                      }
                    }
                  }}
                  className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                >
                  <option value="">-- Escolha a turma semanal desejada --</option>
                  {classes.map(c => {
                    const enrolled = getTurmaStudents(c.id).length;
                    const vagas = c.capacidade_maxima - enrolled;
                    return (
                      <option key={c.id} value={c.id}>
                        {c.nome} • {c.curso_nome} ({c.dia_semana} {c.horario_inicio}-{c.horario_fim}) — {vagas > 0 ? `${vagas} vagas livres` : 'LOTADA'}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Data da Matrícula</label>
                  <input
                    name="data_matricula"
                    type="date"
                    defaultValue={new Date().toISOString().split('T')[0]}
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Data de Início das Aulas</label>
                  <input
                    name="data_inicio"
                    type="date"
                    defaultValue={new Date().toISOString().split('T')[0]}
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Mensalidade (R$)</label>
                  <input
                    id="enroll_valor_mensalidade"
                    name="valor_mensalidade"
                    type="number"
                    step="0.01"
                    defaultValue="280.00"
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800 outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Tipo de Desconto</label>
                  <select
                    name="tipo_desconto"
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="nenhum">Nenhum</option>
                    <option value="irmao">Irmão (Família)</option>
                    <option value="indicacao">Indicação</option>
                    <option value="bolsa">Bolsa</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Desconto (%)</label>
                  <input
                    name="desconto_percentual"
                    type="number"
                    defaultValue="0"
                    min="0"
                    max="100"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input name="aula_experimental" type="checkbox" id="aula_exp" className="rounded text-amber-600" />
                <label htmlFor="aula_exp" className="text-xs text-slate-600 font-medium">É uma aula experimental / cortesia</label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Observações da Matrícula</label>
                <input
                  name="observacoes"
                  placeholder="Informações do contrato ou condições especiais..."
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowEnrollmentModal(false)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Confirmar Matrícula</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: NOVA TURMA */}
      {showClassModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Criar Nova Turma</h3>
              <button onClick={() => setShowClassModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateClass} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome da Turma</label>
                <input
                  name="nome"
                  required
                  placeholder="Ex: Aquarela Avançada Quarta Tarde"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Curso / Modalidade</label>
                  <select name="curso_id" required className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    {courses.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Estúdio / Sala (Cap. 9)</label>
                  <select name="sala_id" required className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    {rooms.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Professor Responsável</label>
                  <select name="professor_id" required className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    {teachers.map(t => <option key={t.id} value={t.id}>{t.nome}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Faixa Etária</label>
                  <select name="faixa_etaria" className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    <option value="INFANTIL">INFANTIL (7 a 10 anos)</option>
                    <option value="JUVENIL">JUVENIL (11 a 17 anos)</option>
                    <option value="ADULTO">ADULTO (18 a 65 anos)</option>
                    <option value="TERCEIRA_IDADE">TERCEIRA IDADE (65+)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Dia da Semana</label>
                  <select name="dia_semana" className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    <option value="SEGUNDA">Segunda-feira</option>
                    <option value="TERCA">Terça-feira</option>
                    <option value="QUARTA">Quarta-feira</option>
                    <option value="QUINTA">Quinta-feira</option>
                    <option value="SEXTA">Sexta-feira</option>
                    <option value="SABADO">Sábado</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Turno</label>
                  <select name="turno" className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500">
                    <option value="MANHA">Manhã</option>
                    <option value="TARDE">Tarde</option>
                    <option value="NOITE">Noite</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Horário de Início (HH:MM)</label>
                  <input
                    name="horario_inicio"
                    type="text"
                    defaultValue="14:00"
                    placeholder="14:00"
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Horário de Término (HH:MM)</label>
                  <input
                    name="horario_fim"
                    type="text"
                    defaultValue="16:00"
                    placeholder="16:00"
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="p-2.5 bg-amber-50 rounded-lg text-xs text-amber-800 font-medium">
                🔒 Teto máximo fixo em <strong>9 alunos</strong> conforme diretriz inegociável da escola.
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowClassModal(false)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Salvar Turma</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: BAIXA DE PAGAMENTO */}
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
