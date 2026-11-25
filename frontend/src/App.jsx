import React, { useState, useEffect } from 'react';
import {
  Palette, Users, BookOpen, Calendar, CreditCard, MessageSquare,
  HardDrive, LogOut, Plus, CheckCircle, AlertTriangle, FileText,
  DollarSign, TrendingUp, ShieldCheck, Clock, Download, RefreshCw, X,
  GraduationCap, Check, Edit, Trash2, Briefcase, Phone, Mail, Menu,
  Search, UserCheck, Shield, ChevronDown, Filter, BarChart2, Cloud, Upload
} from 'lucide-react';
import { api, authStorage } from './services/api';

export default function App() {
  const [user, setUser] = useState(authStorage.getUser());
  const [token, setToken] = useState(authStorage.getToken());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
  const [remoteBackupStatus, setRemoteBackupStatus] = useState(null);
  const [remoteBackups, setRemoteBackups] = useState([]);
  const [remoteConfigForm, setRemoteConfigForm] = useState({
    supabase_url: '',
    service_role_key: '',
    bucket: 'backups',
    prefixo: 'escola-artes',
    auto_enviar_ao_criar: false,
  });
  const [remoteBusy, setRemoteBusy] = useState(false);

  // Estados de login
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loginError, setLoginError] = useState('');

  // Modais de Cursos
  const [showCourseModal, setShowCourseModal] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);

  // Modais de Professores
  const [showTeacherModal, setShowTeacherModal] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState(null);

  // Modais de Alunos e Matrículas
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [showEnrollmentModal, setShowEnrollmentModal] = useState(false);
  const [editingEnrollment, setEditingEnrollment] = useState(null);
  const [preselectedStudentId, setPreselectedStudentId] = useState(null);

  // Modais de Turmas, Salas, Financeiro e Usuários
  const [showClassModal, setShowClassModal] = useState(false);
  const [editingClass, setEditingClass] = useState(null);
  const [classSelectedCourses, setClassSelectedCourses] = useState([]);
  const [classSalaId, setClassSalaId] = useState('');
  const [classCapacidade, setClassCapacidade] = useState('9');
  const [showRoomModal, setShowRoomModal] = useState(false);
  const [editingRoom, setEditingRoom] = useState(null);
  const [enrollSelectedTurmaId, setEnrollSelectedTurmaId] = useState('');
  const [enrollSelectedCursoId, setEnrollSelectedCursoId] = useState('');
  const [showPayModal, setShowPayModal] = useState(null);
  const [payMethod, setPayMethod] = useState('PIX');
  const [payValue, setPayValue] = useState('');
  const [users, setUsers] = useState([]);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userFormRole, setUserFormRole] = useState('Direção');
  const [modalError, setModalError] = useState('');

  // Filtros Financeiro & DRE
  const [invoiceFilter, setInvoiceFilter] = useState('TODAS');
  const [invoiceSearch, setInvoiceSearch] = useState('');
  const [invoiceMonthFilter, setInvoiceMonthFilter] = useState('TODOS');
  const [invoiceYearFilter, setInvoiceYearFilter] = useState('TODOS');
  const [invoiceStudentFilter, setInvoiceStudentFilter] = useState('TODOS');
  const [financialDre, setFinancialDre] = useState(null);

  // Sub-abas e relatórios de Frequência / Diário
  const [attendanceSubTab, setAttendanceSubTab] = useState('chamada'); // 'chamada' | 'turmas' | 'aluno'
  const [attendanceClassesSummary, setAttendanceClassesSummary] = useState([]);
  const [selectedStudentForHistory, setSelectedStudentForHistory] = useState('');
  const [studentAttendanceHistory, setStudentAttendanceHistory] = useState(null);
  const [loadingStudentHistory, setLoadingStudentHistory] = useState(false);

  const toLocalISODate = (d = new Date()) => {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const isMinorBirthDate = (dateStr) => {
    if (!dateStr) return false;
    const parts = String(dateStr).split('T')[0].split('-');
    if (parts.length !== 3) return false;
    const [y, m, d] = parts.map(Number);
    const hoje = new Date();
    let idade = hoje.getFullYear() - y;
    if (hoje.getMonth() + 1 < m || (hoje.getMonth() + 1 === m && hoje.getDate() < d)) {
      idade -= 1;
    }
    return idade < 18;
  };

  // Estados para Frequência / Diário
  const [selectedClassForAttendance, setSelectedClassForAttendance] = useState('');
  const [attendanceDate, setAttendanceDate] = useState(() => toLocalISODate());
  const [lessonTopic, setLessonTopic] = useState('');
  const [lessonContent, setLessonContent] = useState('');
  const [lessonMaterials, setLessonMaterials] = useState('');
  const [attendanceRecords, setAttendanceRecords] = useState({});
  const [classLessonsHistory, setClassLessonsHistory] = useState([]);

  // Permissões
  const isProfessor = user?.role === 'Professor' || user?.role === 'PROFESSOR';
  const isAdminOrCoord = user?.role === 'Direção' || user?.role === 'Coordenação' || user?.role === 'DIRECAO' || user?.role === 'COORDENACAO';

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

      if (isAdminOrCoord) {
        api.getUsers().then(u => setUsers(u)).catch(() => setUsers([]));
      }

      if (activeTab === 'attendance') {
        api.getAttendanceClassesSummary().then(cs => setAttendanceClassesSummary(cs)).catch(() => setAttendanceClassesSummary([]));
      }

      if (activeTab === 'backups') {
        api.getRemoteBackupStatus()
          .then(st => {
            setRemoteBackupStatus(st);
            setRemoteConfigForm(prev => ({
              ...prev,
              supabase_url: st.supabase_url || prev.supabase_url || '',
              bucket: st.bucket || 'backups',
              prefixo: st.prefixo || 'escola-artes',
              auto_enviar_ao_criar: Boolean(st.auto_enviar_ao_criar),
              service_role_key: '',
            }));
            if (st.configurado) {
              api.getRemoteBackups().then(rb => setRemoteBackups(rb)).catch(() => setRemoteBackups([]));
            } else {
              setRemoteBackups([]);
            }
          })
          .catch(() => setRemoteBackupStatus(null));
      }

      // Carrega DRE do mês
      const hoje = new Date();
      const primeiroDia = toLocalISODate(new Date(hoje.getFullYear(), hoje.getMonth(), 1));
      const ultimoDia = toLocalISODate(new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0));
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

  // Atualiza DRE filtrado por mês, ano e aluno na aba Financeiro
  useEffect(() => {
    if (!token || activeTab !== 'financial') return;
    const hoje = new Date();
    const currentYear = hoje.getFullYear();
    const targetYear = invoiceYearFilter !== 'TODOS' ? parseInt(invoiceYearFilter, 10) : currentYear;

    let inicio;
    let fim;
    if (invoiceMonthFilter !== 'TODOS') {
      const targetMonth = parseInt(invoiceMonthFilter, 10);
      const lastDay = new Date(targetYear, targetMonth, 0).getDate();
      const mm = String(targetMonth).padStart(2, '0');
      inicio = `${targetYear}-${mm}-01`;
      fim = `${targetYear}-${mm}-${String(lastDay).padStart(2, '0')}`;
    } else if (invoiceYearFilter !== 'TODOS') {
      inicio = `${targetYear}-01-01`;
      fim = `${targetYear}-12-31`;
    } else {
      const currMonth = hoje.getMonth() + 1;
      const lastDay = new Date(currentYear, currMonth, 0).getDate();
      const mm = String(currMonth).padStart(2, '0');
      inicio = `${currentYear}-${mm}-01`;
      fim = `${currentYear}-${mm}-${String(lastDay).padStart(2, '0')}`;
    }

    const alunoId = invoiceStudentFilter !== 'TODOS' ? invoiceStudentFilter : null;
    api.getDRE(inicio, fim, alunoId)
      .then(data => setFinancialDre(data))
      .catch(() => setFinancialDre(null));
  }, [token, activeTab, invoiceMonthFilter, invoiceYearFilter, invoiceStudentFilter, invoices.length]);

  // Se selecionar aluno para histórico de frequência
  useEffect(() => {
    if (selectedStudentForHistory) {
      setLoadingStudentHistory(true);
      api.getAttendanceStudentHistory(selectedStudentForHistory)
        .then(data => setStudentAttendanceHistory(data))
        .catch(err => {
          showToast(err.message || 'Erro ao carregar histórico do aluno.', 'error');
          setStudentAttendanceHistory(null);
        })
        .finally(() => setLoadingStudentHistory(false));
    } else {
      setStudentAttendanceHistory(null);
      setLoadingStudentHistory(false);
    }
  }, [selectedStudentForHistory]);

  // Se trocar a aba de frequência para turmas, atualiza resumo
  useEffect(() => {
    if (activeTab === 'attendance' && attendanceSubTab === 'turmas') {
      api.getAttendanceClassesSummary()
        .then(cs => setAttendanceClassesSummary(cs))
        .catch(() => setAttendanceClassesSummary([]));
    }
  }, [activeTab, attendanceSubTab]);

  // Se trocar a turma na frequência, carrega histórico de aulas
  useEffect(() => {
    if (selectedClassForAttendance) {
      api.getLessons(selectedClassForAttendance)
        .then((data) => setClassLessonsHistory(data))
        .catch(() => setClassLessonsHistory([]));
      
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
            <span className="text-xs text-slate-400">Acesso restrito e seguro • Escola de Artes Helena Barufaldi</span>
          </div>
        </div>
      </div>
    );
  }

  // --- SUBMISSION HANDLERS ---

  // 1. Cadastrar / Editar Aluno
  const handleSaveStudent = async (e) => {
    e.preventDefault();
    setModalError('');
    const formData = new FormData(e.target);
    const dataNascimento = formData.get('data_nascimento');
    const isMenor = isMinorBirthDate(dataNascimento);

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
      if (editingStudent) {
        await api.updateStudent(editingStudent.id, {
          nome: payload.nome,
          data_nascimento: payload.data_nascimento,
          cpf: payload.cpf,
          telefone: payload.telefone,
          email: payload.email,
          endereco: payload.endereco,
          alergias: payload.alergias,
          autorizacao_imagem: payload.autorizacao_imagem,
        });
        if (payload.responsavel && editingStudent.responsavel) {
          await api.updateGuardian(editingStudent.id, payload.responsavel);
        }
        showToast('Aluno e responsável atualizados com sucesso!');
        setEditingStudent(null);
      } else {
        await api.createStudent(payload);
        showToast('Aluno cadastrado com sucesso!');
      }
      setShowStudentModal(false);
      loadDashboardData();
    } catch (err) {
      setModalError(err.message || 'Erro ao salvar aluno.');
      showToast(err.message, 'error');
    }
  };

  // 2. Cadastrar / Editar Curso
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

  const handleUpdateCourse = async (e) => {
    e.preventDefault();
    if (!editingCourse) return;
    const formData = new FormData(e.target);
    const payload = {
      nome: formData.get('nome'),
      descricao: formData.get('descricao') || null,
      duracao_meses: parseInt(formData.get('duracao_meses') || '12'),
      valor_mensalidade: parseFloat(formData.get('valor_mensalidade') || '0'),
      ativo: formData.get('ativo') === 'on'
    };

    try {
      await api.updateCourse(editingCourse.id, payload);
      showToast(`Modalidade '${payload.nome}' atualizada com sucesso!`);
      setEditingCourse(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteCourse = async (course) => {
    const confirmMsg = `Deseja realmente excluir ou desativar o curso '${course.nome}'?`;
    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await api.deleteCourse(course.id);
      showToast(res.mensagem || 'Curso processado com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 3. Cadastrar / Editar Professor
  const handleCreateTeacher = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const subId = formData.get('substituto_id');
    const payload = {
      nome: formData.get('nome'),
      email: formData.get('email'),
      telefone: formData.get('telefone') || null,
      endereco: formData.get('endereco') || null,
      especialidades: formData.get('especialidades') || null,
      disponibilidade: formData.get('disponibilidade') || null,
      substituto_id: subId && subId !== '' ? parseInt(subId) : null,
    };

    try {
      await api.createTeacher(payload);
      showToast(`Professor(a) '${payload.nome}' cadastrado(a) com sucesso!`);
      setShowTeacherModal(false);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleUpdateTeacher = async (e) => {
    e.preventDefault();
    if (!editingTeacher) return;
    const formData = new FormData(e.target);
    const subId = formData.get('substituto_id');
    const payload = {
      nome: formData.get('nome'),
      email: formData.get('email'),
      telefone: formData.get('telefone') || null,
      endereco: formData.get('endereco') || null,
      especialidades: formData.get('especialidades') || null,
      disponibilidade: formData.get('disponibilidade') || null,
      substituto_id: subId && subId !== '' ? parseInt(subId) : null,
      ativo: formData.get('ativo') === 'on',
    };

    try {
      await api.updateTeacher(editingTeacher.id, payload);
      showToast(`Professor(a) '${payload.nome}' atualizado(a) com sucesso!`);
      setEditingTeacher(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteTeacher = async (teacher) => {
    const confirmMsg = `Deseja realmente excluir ou desativar o(a) professor(a) '${teacher.nome}'?`;
    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await api.deleteTeacher(teacher.id);
      showToast(res.mensagem || 'Professor processado com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 4. Matricular Aluno em Turma/Curso
  const handleCreateEnrollment = async (e) => {
    e.preventDefault();
    setModalError('');
    const formData = new FormData(e.target);
    const descTipo = formData.get('tipo_desconto');
    const payload = {
      aluno_id: parseInt(formData.get('aluno_id')),
      turma_id: parseInt(formData.get('turma_id')),
      curso_id: formData.get('curso_id') ? parseInt(formData.get('curso_id')) : (enrollSelectedCursoId ? parseInt(enrollSelectedCursoId) : null),
      data_matricula: formData.get('data_matricula'),
      data_inicio: formData.get('data_inicio'),
      data_termino_previsto: formData.get('data_termino_previsto') || null,
      valor_mensalidade: parseFloat(formData.get('valor_mensalidade') || '0'),
      desconto_percentual: parseFloat(formData.get('desconto_percentual') || '0'),
      tipo_desconto: descTipo && descTipo !== 'nenhum' ? descTipo : null,
      dia_vencimento: parseInt(formData.get('dia_vencimento') || '10'),
      quantidade_parcelas: parseInt(formData.get('quantidade_parcelas') || '12'),
      aula_experimental: formData.get('aula_experimental') === 'on',
      observacoes: formData.get('observacoes') || null,
    };

    try {
      const created = await api.createEnrollment(payload);
      if (payload.aula_experimental) {
        showToast('Matrícula experimental registrada (sem cobrança financeira).');
      } else {
        const qtd = created?.total_parcelas_geradas ?? payload.quantidade_parcelas;
        showToast(`Aluno matriculado e ${qtd} parcela(s) gerada(s) no Financeiro!`);
      }
      setShowEnrollmentModal(false);
      setPreselectedStudentId(null);
      setEnrollSelectedTurmaId('');
      setEnrollSelectedCursoId('');
      await loadDashboardData();
    } catch (err) {
      setModalError(err.message || 'Erro ao realizar matrícula.');
      showToast(err.message, 'error');
    }
  };

  // 4.1. Atualizar Matrícula / Contrato
  const handleUpdateEnrollment = async (e) => {
    e.preventDefault();
    if (!editingEnrollment) return;
    setModalError('');
    const formData = new FormData(e.target);
    const descTipo = formData.get('tipo_desconto');
    const payload = {
      status: formData.get('status'),
      valor_mensalidade: parseFloat(formData.get('valor_mensalidade') || '0'),
      desconto_percentual: parseFloat(formData.get('desconto_percentual') || '0'),
      tipo_desconto: descTipo && descTipo !== 'nenhum' ? descTipo : null,
      dia_vencimento: parseInt(formData.get('dia_vencimento') || '10'),
      quantidade_parcelas: parseInt(formData.get('quantidade_parcelas') || '12'),
      motivo_cancelamento: formData.get('motivo_cancelamento') || null,
      contrato_assinado: formData.get('contrato_assinado') === 'on',
      observacoes: formData.get('observacoes') || null,
    };

    try {
      const updated = await api.updateEnrollment(editingEnrollment.id, payload);
      const qtd = updated?.total_parcelas_geradas ?? 0;
      if (payload.status === 'CANCELADA') {
        showToast('Matrícula cancelada e parcelas em aberto canceladas no Financeiro!');
      } else if (payload.status === 'TRANCADA') {
        showToast('Matrícula trancada e parcelas futuras canceladas no Financeiro!');
      } else if (payload.status === 'EXPERIMENTAL') {
        showToast('Matrícula alterada para experimental e parcelas em aberto canceladas!');
      } else {
        showToast(
          payload.status === 'ATIVA' && qtd > 0
            ? `Matrícula atualizada! ${qtd} parcela(s) ativa(s) sincronizada(s) no Financeiro.`
            : 'Matrícula atualizada com sucesso!'
        );
      }
      setEditingEnrollment(null);
      await loadDashboardData();
    } catch (err) {
      setModalError(err.message || 'Erro ao atualizar matrícula.');
      showToast(err.message, 'error');
    }
  };

  // 4.1b. Gerar Parcelas de uma Matrícula ou Sincronizar Todas
  const handleGenerateEnrollmentInvoices = async (matriculaId) => {
    try {
      const res = await api.generateEnrollmentInvoices(matriculaId);
      showToast(res.mensagem || 'Parcelas geradas com sucesso!');
      await loadDashboardData();
    } catch (err) {
      showToast(err.message || 'Erro ao gerar parcelas.', 'error');
    }
  };

  const handleSyncAllInvoices = async () => {
    try {
      const res = await api.syncEnrollmentInvoices();
      showToast(res.mensagem || 'Parcelas sincronizadas!');
      await loadDashboardData();
    } catch (err) {
      showToast(err.message || 'Erro ao sincronizar parcelas.', 'error');
    }
  };

  // 4.2. Usuários: Criar / Editar Usuário e RBAC
  const handleSaveUser = async (e) => {
    e.preventDefault();
    setModalError('');
    const formData = new FormData(e.target);
    const profIdVal = formData.get('professor_id');
    const roleVal = userFormRole || formData.get('role');
    const payload = {
      nome: formData.get('nome'),
      email: formData.get('email'),
      role: roleVal,
      professor_id: roleVal === 'Professor' && profIdVal ? parseInt(profIdVal) : null,
      ativo: formData.get('ativo') === 'on',
    };
    const senhaVal = formData.get('senha');
    if (senhaVal && senhaVal.trim()) {
      payload.senha = senhaVal.trim();
    }

    try {
      if (editingUser) {
        await api.updateUser(editingUser.id, payload);
        showToast('Usuário atualizado com sucesso!');
        setEditingUser(null);
      } else {
        await api.createUser(payload);
        showToast('Usuário criado com sucesso!');
      }
      setShowUserModal(false);
      loadDashboardData();
    } catch (err) {
      const msg = typeof err === 'string' ? err : (err?.message || 'Erro ao salvar usuário.');
      setModalError(msg);
      showToast(msg, 'error');
    }
  };

  const handleToggleUserStatus = async (usr) => {
    try {
      await api.updateUser(usr.id, { ativo: !usr.ativo });
      showToast(`Usuário ${usr.ativo ? 'desativado' : 'ativado'} com sucesso!`);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 5. Cadastrar / Editar / Excluir Turma e Salas
  const openNewClassModal = () => {
    setEditingClass(null);
    setClassSelectedCourses([]);
    const firstRoom = rooms[0];
    setClassSalaId(firstRoom ? String(firstRoom.id) : '');
    setClassCapacidade(firstRoom ? String(firstRoom.capacidade) : '9');
    setShowClassModal(true);
  };

  const openEditClassModal = (cls) => {
    setEditingClass(cls);
    const ids = cls.cursos_ids && cls.cursos_ids.length > 0
      ? cls.cursos_ids
      : (cls.curso_id ? [cls.curso_id] : []);
    setClassSelectedCourses(ids);
    setClassSalaId(String(cls.sala_id));
    setClassCapacidade(String(cls.capacidade_maxima));
    setShowClassModal(true);
  };

  const toggleClassCourse = (courseId) => {
    setClassSelectedCourses((prev) =>
      prev.includes(courseId) ? prev.filter((id) => id !== courseId) : [...prev, courseId]
    );
  };

  const handleSaveClass = async (e) => {
    e.preventDefault();
    if (classSelectedCourses.length === 0) {
      showToast('Selecione pelo menos um curso/modalidade para a turma.', 'error');
      return;
    }
    const formData = new FormData(e.target);
    const faixaEtaria = formData.get('faixa_etaria');
    if (!faixaEtaria) {
      showToast('Selecione a faixa etária da turma.', 'error');
      return;
    }

    const salaId = parseInt(formData.get('sala_id'), 10);
    const capacidade = parseInt(formData.get('capacidade_maxima'), 10);
    if (!capacidade || capacidade < 1) {
      showToast('Informe uma capacidade máxima válida (mínimo 1 aluno).', 'error');
      return;
    }

    const payload = {
      nome: formData.get('nome'),
      curso_id: classSelectedCourses[0],
      cursos_ids: classSelectedCourses,
      sala_id: salaId,
      professor_id: parseInt(formData.get('professor_id'), 10),
      faixa_etaria: faixaEtaria,
      dia_semana: formData.get('dia_semana'),
      turno: formData.get('turno'),
      horario_inicio: formData.get('horario_inicio'),
      horario_fim: formData.get('horario_fim'),
      capacidade_maxima: capacidade,
      ...(editingClass ? { ativa: formData.get('ativa') === 'on' } : {}),
    };

    try {
      if (editingClass) {
        await api.updateClass(editingClass.id, payload);
        showToast('Turma atualizada com sucesso!');
      } else {
        await api.createClass(payload);
        showToast('Turma criada com sucesso!');
      }
      setShowClassModal(false);
      setEditingClass(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteClass = async (cls) => {
    const confirmMsg = `Deseja realmente excluir ou desativar a turma '${cls.nome}'?`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await api.deleteClass(cls.id);
      showToast(res.mensagem || 'Turma processada com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleSaveRoom = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = {
      nome: formData.get('nome'),
      capacidade: parseInt(formData.get('capacidade'), 10),
      descricao: formData.get('descricao') || null,
      ...(editingRoom ? { ativa: formData.get('ativa') === 'on' } : {}),
    };
    try {
      if (editingRoom) {
        await api.updateRoom(editingRoom.id, payload);
        showToast(`Sala '${payload.nome}' atualizada com sucesso!`);
      } else {
        await api.createRoom(payload);
        showToast(`Sala '${payload.nome}' cadastrada com sucesso!`);
      }
      setShowRoomModal(false);
      setEditingRoom(null);
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteRoom = async (room) => {
    const confirmMsg = `Deseja realmente excluir ou desativar a sala '${room.nome}'?`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await api.deleteRoom(room.id);
      showToast(res.mensagem || 'Sala processada com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteStudent = async (student) => {
    const confirmMsg = `Deseja realmente excluir ou desativar o(a) aluno(a) '${student.nome}'?`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await api.deleteStudent(student.id);
      showToast(res.mensagem || 'Aluno processado com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteEnrollment = async (enr) => {
    const alunoNome = enr.aluno_nome || `Aluno #${enr.aluno_id}`;
    const confirmMsg = `Deseja realmente excluir a matrícula de '${alunoNome}'? (Parcelas não pagas vinculadas serão removidas.)`;
    if (!window.confirm(confirmMsg)) return;
    try {
      const res = await api.deleteEnrollment(enr.id);
      showToast(res.mensagem || 'Matrícula excluída com sucesso!');
      loadDashboardData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 6. Salvar Diário de Classe e Frequência
  const handleSaveAttendance = async (e) => {
    e.preventDefault();
    if (!selectedClassForAttendance) {
      showToast('Selecione uma turma para lançar a frequência.', 'error');
      return;
    }

    const turmaObj = classes.find(c => c.id === parseInt(selectedClassForAttendance));
    if (!turmaObj) return;

    try {
      const lesson = await api.createLesson({
        turma_id: turmaObj.id,
        professor_id: turmaObj.professor_id,
        data_aula: attendanceDate,
        tema_aula: lessonTopic || 'Aula Regular',
        conteudo_programatico: lessonContent || null,
        materiais_utilizados: lessonMaterials || null,
        observacoes: null
      });

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

      const updatedLessons = await api.getLessons(turmaObj.id);
      setClassLessonsHistory(updatedLessons);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // 7. Quitar Mensalidade
  const handlePayInvoice = async () => {
    if (!showPayModal) return;
    setModalError('');
    try {
      await api.payInvoice(showPayModal.id, {
        valor_pago: parseFloat(payValue || showPayModal.valor_final),
        forma_pagamento: payMethod,
      });
      showToast(`Título quitado com sucesso via ${payMethod}!`);
      setShowPayModal(null);
      loadDashboardData();
    } catch (err) {
      setModalError(err.message || 'Erro ao registrar pagamento.');
      showToast(err.message, 'error');
    }
  };

  // 8. WhatsApp Links
  const handleSendWelcomeWhatsApp = async (matriculaId) => {
    try {
      const data = await api.getEnrollmentWelcomeLink(matriculaId);
      window.open(data.whatsapp_url, '_blank');
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

  // 9. Backups Locais e Remotos (Supabase)
  const refreshBackups = async () => {
    const [bkp, st] = await Promise.all([
      api.getBackups().catch(() => []),
      api.getRemoteBackupStatus().catch(() => null),
    ]);
    setBackups(bkp);
    setRemoteBackupStatus(st);
    if (st?.configurado) {
      const rb = await api.getRemoteBackups().catch(() => []);
      setRemoteBackups(rb);
    } else {
      setRemoteBackups([]);
    }
  };

  const handleBackup = async () => {
    try {
      const res = await api.createBackup();
      if (res?.enviado_remoto) {
        showToast('Backup local gerado e enviado ao Supabase com sucesso!');
      } else if (res?.remoto_mensagem) {
        showToast(`Backup local gerado (aviso remoto: ${res.remoto_mensagem})`, 'error');
      } else {
        showToast('Backup do banco de dados local gerado com sucesso!');
      }
      await refreshBackups();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleSaveRemoteConfig = async (e) => {
    e.preventDefault();
    setRemoteBusy(true);
    try {
      const saved = await api.saveRemoteBackupConfig({
        ...remoteConfigForm,
        service_role_key: remoteConfigForm.service_role_key || null,
        testar_conexao: true,
      });
      setRemoteBackupStatus(saved);
      setRemoteConfigForm(prev => ({ ...prev, service_role_key: '' }));
      showToast('Conexão com Supabase validada e configuração salva!');
      await refreshBackups();
    } catch (err) {
      showToast(err.message || 'Erro ao salvar configuração do Supabase.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handleTestRemoteBackup = async () => {
    setRemoteBusy(true);
    try {
      const res = await api.testRemoteBackup();
      showToast(res.mensagem || 'Conexão com Supabase validada!');
    } catch (err) {
      showToast(err.message || 'Falha ao conectar no Supabase.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handleSyncRemoteNow = async () => {
    setRemoteBusy(true);
    try {
      const res = await api.syncRemoteBackupNow();
      showToast(`Snapshot '${res.arquivo}' gerado e enviado ao Supabase!`);
      await refreshBackups();
    } catch (err) {
      showToast(err.message || 'Erro ao enviar backup para o Supabase.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handleUploadToRemote = async (filename) => {
    setRemoteBusy(true);
    try {
      await api.uploadBackupToRemote(filename);
      showToast(`Arquivo '${filename}' enviado ao Supabase!`);
      await refreshBackups();
    } catch (err) {
      showToast(err.message || 'Erro ao enviar backup.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handlePullFromRemote = async (filename) => {
    setRemoteBusy(true);
    try {
      await api.pullRemoteBackup(filename);
      showToast(`Backup '${filename}' copiado do Supabase para a pasta local!`);
      await refreshBackups();
    } catch (err) {
      showToast(err.message || 'Erro ao copiar backup do Supabase.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handleDeleteRemoteBackup = async (filename) => {
    if (!window.confirm(`Remover o backup remoto '${filename}' do Supabase?`)) return;
    setRemoteBusy(true);
    try {
      await api.deleteRemoteBackup(filename);
      showToast(`Backup remoto '${filename}' excluído do Supabase.`);
      await refreshBackups();
    } catch (err) {
      showToast(err.message || 'Erro ao excluir backup remoto.', 'error');
    } finally {
      setRemoteBusy(false);
    }
  };

  const handleDownloadLocalBackup = async (filename) => {
    try {
      await api.downloadLocalBackup(filename);
    } catch (err) {
      showToast(err.message || 'Erro ao baixar backup local.', 'error');
    }
  };

  const handleDownloadRemoteBackup = async (filename) => {
    try {
      await api.downloadRemoteBackup(filename);
    } catch (err) {
      showToast(err.message || 'Erro ao baixar backup remoto.', 'error');
    }
  };

  // Utilitários
  const formatDateBR = (dateStr) => {
    if (!dateStr) return '-';
    const parts = String(dateStr).split('T')[0].split('-');
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return new Date(dateStr).toLocaleDateString('pt-BR');
  };

  const getStudentEnrollments = (studentId) => {
    return enrollments.filter(e => e.aluno_id === studentId && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
  };

  const getTurmaStudents = (turmaId) => {
    const enrs = enrollments.filter(e => e.turma_id === turmaId && (e.status === 'ATIVA' || e.status === 'EXPERIMENTAL'));
    return enrs.map(e => e.aluno_nome || `Aluno #${e.aluno_id}`);
  };

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Toast Notification - Z-Index 9999 para ficar visível à frente de qualquer modal ou blur */}
      {toast && (
        <div className={`fixed top-6 right-6 z-[9999] max-w-md px-5 py-4 rounded-xl shadow-2xl flex items-center justify-between gap-3 text-sm font-semibold border ${
          toast.type === 'error'
            ? 'bg-red-600 text-white border-red-700 ring-4 ring-red-600/20'
            : 'bg-emerald-600 text-white border-emerald-700 ring-4 ring-emerald-600/20'
        }`}>
          <div className="flex items-center gap-3">
            {toast.type === 'error' ? <AlertTriangle className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
            <span>{toast.message}</span>
          </div>
          <button onClick={() => setToast(null)} className="p-1 hover:bg-white/20 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Overlay Backdrop Mobile */}
      {isMobileMenuOpen && (
        <div
          onClick={() => setIsMobileMenuOpen(false)}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-30 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar de Navegação */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800 transition-transform duration-300 ease-in-out ${
          isMobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-600 flex items-center justify-center text-white shadow-md">
              <Palette className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-bold text-white text-base leading-tight">Helena Barufaldi</h2>
              <span className="text-[11px] font-semibold text-amber-500 uppercase tracking-wider">Escola de Artes</span>
            </div>
          </div>
          {/* Botão Fechar Menu Lateral no Mobile */}
          <button
            onClick={() => setIsMobileMenuOpen(false)}
            className="md:hidden text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
            title="Fechar menu lateral"
            aria-label="Fechar menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {[
            { id: 'dashboard', label: 'Painel Geral', icon: TrendingUp },
            { id: 'students', label: isProfessor ? 'Meus Alunos' : 'Alunos & Responsáveis', icon: Users },
            ...(!isProfessor ? [
              { id: 'courses', label: 'Cursos & Modalidades', icon: BookOpen },
              { id: 'teachers', label: 'Professores & Docentes', icon: Briefcase },
              { id: 'enrollments', label: 'Matrículas & Contratos', icon: GraduationCap },
            ] : []),
            { id: 'classes', label: isProfessor ? 'Minhas Turmas' : 'Turmas & Horários', icon: Calendar },
            ...(!isProfessor ? [
              { id: 'rooms', label: 'Salas & Capacidade (9)', icon: Palette },
              { id: 'financial', label: 'Financeiro & DRE', icon: DollarSign },
            ] : []),
            { id: 'attendance', label: 'Frequência & Diário', icon: Clock },
            ...(!isProfessor ? [
              { id: 'backups', label: 'Backups do Sistema', icon: HardDrive },
            ] : []),
            ...(isAdminOrCoord ? [
              { id: 'users', label: 'Usuários & Acessos', icon: UserCheck },
            ] : []),
          ].map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsMobileMenuOpen(false);
                }}
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
      <main className="flex-1 flex flex-col overflow-y-auto min-w-0">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 px-4 sm:px-6 md:px-8 py-3.5 sm:py-4 flex items-center justify-between sticky top-0 z-20 shadow-sm">
          <div className="flex items-center gap-3 min-w-0">
            {/* Botão Hamburger Mobile */}
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="md:hidden p-2 -ml-2 text-slate-700 hover:text-amber-700 hover:bg-slate-100 rounded-lg transition shrink-0"
              title="Abrir menu lateral"
              aria-label="Abrir menu lateral"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="min-w-0">
              <h1 className="text-base sm:text-lg md:text-xl font-bold text-slate-800 truncate">
                {activeTab === 'dashboard' && 'Painel Geral de Indicadores'}
                {activeTab === 'students' && (isProfessor ? 'Meus Alunos' : 'Gestão de Alunos e Responsáveis')}
                {activeTab === 'courses' && 'Catálogo de Cursos & Modalidades'}
                {activeTab === 'teachers' && 'Corpo Docente e Professores'}
                {activeTab === 'enrollments' && 'Matrículas & Contratos'}
                {activeTab === 'classes' && (isProfessor ? 'Minhas Turmas Atribuídas' : 'Turmas e Capacidade Máxima')}
                {activeTab === 'rooms' && 'Estúdios Físicos (Teto de 9 Alunos)'}
                {activeTab === 'financial' && 'Gestão Financeira & DRE'}
                {activeTab === 'attendance' && 'Diário de Classe & Frequência'}
                {activeTab === 'backups' && 'Segurança & Backup Local SQLite'}
                {activeTab === 'users' && 'Gestão de Usuários & Perfis de Acesso'}
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">Unidade Nova Odessa/SP • Porta 8080 • Servidor Local</p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <button
              onClick={loadDashboardData}
              className="p-2 sm:px-3 text-slate-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition border border-slate-200 flex items-center gap-1.5 text-xs font-semibold"
              title="Atualizar dados"
            >
              <RefreshCw className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Atualizar</span>
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div className="p-4 sm:p-6 md:p-8 space-y-6">

          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
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
                    <span className="text-xs font-semibold text-slate-400 uppercase">Modalidades / Cursos</span>
                    <h3 className="text-2xl font-bold text-slate-800 mt-1">{courses.length}</h3>
                    <p className="text-xs text-slate-500 mt-1">{teachers.length} professores ativos</p>
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

              {/* Salas e Capacidade */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <Palette className="w-5 h-5 text-amber-600" />
                  Ocupação dos Estúdios Físicos (Capacidade Configurável por Sala)
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

              {/* Resumo DRE */}
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
              <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Cadastro de Alunos e Cursos Matriculados</h3>
                  <p className="text-xs text-slate-500">Regra: Alunos menores exigem responsável legal único. Vincule cursos diretamente no botão "+ Matricular".</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={api.exportStudentsUrl}
                    className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" /> Exportar CSV
                  </a>
                  <button
                    onClick={() => {
                      setEditingStudent(null);
                      setModalError('');
                      setShowStudentModal(true);
                    }}
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
                              Nasc: {formatDateBR(st.data_nascimento)}
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
                          <td className="px-6 py-4 text-right space-x-1 whitespace-nowrap">
                            <button
                              onClick={() => {
                                setEditingStudent(st);
                                setModalError('');
                                setShowStudentModal(true);
                              }}
                              className="p-1.5 text-slate-500 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition inline-flex items-center"
                              title="Editar dados do aluno e responsável"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            {!isProfessor && (
                              <button
                                onClick={() => handleDeleteStudent(st)}
                                className="p-1.5 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded-lg transition inline-flex items-center"
                                title="Excluir ou desativar aluno"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => {
                                setPreselectedStudentId(st.id);
                                setModalError('');
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
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Catálogo de Modalidades de Arte</h3>
                  <p className="text-xs text-slate-500">Cadastre, edite e gerencie as modalidades artísticas e mensalidades da escola.</p>
                </div>
                <button
                  onClick={() => setShowCourseModal(true)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
                >
                  <Plus className="w-3.5 h-3.5" /> Novo Curso / Modalidade
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {courses.map((course) => {
                  const classHasCourse = (c) =>
                    Array.isArray(c.cursos_ids) && c.cursos_ids.length > 0
                      ? c.cursos_ids.includes(course.id)
                      : c.curso_id === course.id;
                  const courseClasses = classes.filter(classHasCourse);
                  const enrolledCount = enrollments.filter(e => {
                    if (e.status !== 'ATIVA' && e.status !== 'EXPERIMENTAL') return false;
                    if (e.curso_id) return e.curso_id === course.id;
                    const t = classes.find(c => c.id === e.turma_id);
                    return t && classHasCourse(t);
                  }).length;

                  return (
                    <div key={course.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:border-amber-400 transition">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
                            <BookOpen className="w-4 h-4" />
                          </span>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              course.ativo ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {course.ativo ? 'Ativo' : 'Inativo'}
                            </span>
                            <button
                              onClick={() => setEditingCourse(course)}
                              className="p-1 text-slate-400 hover:text-amber-700 hover:bg-amber-50 rounded transition"
                              title="Editar modalidade"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteCourse(course)}
                              className="p-1 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded transition"
                              title="Excluir ou desativar modalidade"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
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

          {/* TAB 4: PROFESSORES & DOCENTES */}
          {activeTab === 'teachers' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Corpo Docente e Professores</h3>
                  <p className="text-xs text-slate-500">Cadastre os professores da escola para vinculá-los às turmas semanais.</p>
                </div>
                <button
                  onClick={() => setShowTeacherModal(true)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
                >
                  <Plus className="w-3.5 h-3.5" /> Novo Professor
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {teachers.map((t) => {
                  const teacherClasses = classes.filter(c => c.professor_id === t.id);
                  return (
                    <div key={t.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:border-amber-400 transition">
                      <div>
                        <div className="flex items-center justify-between">
                          <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 font-bold flex items-center justify-center text-sm">
                            {t.nome.charAt(0)}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              t.ativo ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {t.ativo ? 'Ativo' : 'Inativo'}
                            </span>
                            <button
                              onClick={() => setEditingTeacher(t)}
                              className="p-1 text-slate-400 hover:text-amber-700 hover:bg-amber-50 rounded transition"
                              title="Editar professor"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteTeacher(t)}
                              className="p-1 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded transition"
                              title="Excluir ou desativar professor"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        <h4 className="text-base font-bold text-slate-800 mt-3">{t.nome}</h4>
                        <div className="space-y-1 mt-2 text-xs text-slate-500">
                          <p className="flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-slate-400" /> {t.email}
                          </p>
                          {t.telefone && (
                            <p className="flex items-center gap-1.5">
                              <Phone className="w-3.5 h-3.5 text-slate-400" /> {t.telefone}
                            </p>
                          )}
                        </div>

                        {t.especialidades && (
                          <div className="mt-3">
                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide block mb-1">
                              Especialidades:
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {t.especialidades.split(',').map((esp, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium">
                                  {esp.trim()}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-slate-500">Turmas lecionadas:</span>
                        <span className="font-bold text-amber-800">{teacherClasses.length} turmas</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {teachers.length === 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-8 text-center">
                  <Briefcase className="w-10 h-10 text-amber-700 mx-auto mb-2" />
                  <h4 className="font-bold text-amber-900 text-base">Nenhum professor cadastrado</h4>
                  <p className="text-xs text-amber-800 mt-1 max-w-md mx-auto">
                    Cadastre os professores da escola para poder vinculá-los às turmas e horários de aula.
                  </p>
                  <button
                    onClick={() => setShowTeacherModal(true)}
                    className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow"
                  >
                    Cadastrar Primeiro Professor
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: MATRÍCULAS & CONTRATOS */}
          {activeTab === 'enrollments' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Matrículas Ativas e Vínculos de Alunos</h3>
                  <p className="text-xs text-slate-500">Vínculo direto entre Aluno e Turma/Curso com contrato e controle de desconto.</p>
                </div>
                <button
                  onClick={() => {
                    setPreselectedStudentId(null);
                    setModalError('');
                    setShowEnrollmentModal(true);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
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
                          {enr.curso_nome && (
                            <span className="text-[11px] text-slate-500 block">{enr.curso_nome}</span>
                          )}
                          {enr.aula_experimental && (
                            <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">Aula Experimental</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs">
                          {formatDateBR(enr.data_inicio)}
                        </td>
                        <td className="px-6 py-4">
                          <span className="font-bold text-slate-800 block">
                            R$ {(enr.valor_com_desconto ?? enr.valor_mensalidade).toFixed(2)}
                          </span>
                          <span className="text-[11px] text-slate-500 block">
                            Dia {enr.dia_vencimento || 10} • {enr.quantidade_parcelas || 12}x
                          </span>
                          {!enr.aula_experimental && (
                            <span className={`text-[10px] font-semibold block mt-0.5 ${
                              (enr.total_parcelas_geradas || 0) >= (enr.quantidade_parcelas || 12)
                                ? 'text-emerald-600'
                                : 'text-amber-700'
                            }`}>
                              {enr.total_parcelas_geradas || 0}/{enr.quantidade_parcelas || 12} parcelas no financeiro
                            </span>
                          )}
                          {enr.desconto_percentual > 0 && (
                            <span className="text-[11px] text-emerald-600 block">
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
                          {enr.contrato_assinado ? (
                            <span className="block text-[10px] text-emerald-600 mt-0.5 font-medium">Contrato assinado</span>
                          ) : (
                            <span className="block text-[10px] text-amber-600 mt-0.5 font-medium">Aguardando ass.</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right space-x-1 whitespace-nowrap">
                          {enr.status === 'ATIVA' && !enr.aula_experimental && (enr.total_parcelas_geradas || 0) < (enr.quantidade_parcelas || 12) && (
                            <button
                              onClick={() => handleGenerateEnrollmentInvoices(enr.id)}
                              className="px-2.5 py-1.5 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition inline-flex items-center gap-1 shadow-sm"
                              title="Gerar mensalidades faltantes no Financeiro"
                            >
                              <CreditCard className="w-3.5 h-3.5" /> Gerar Parcelas
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setEditingEnrollment(enr);
                              setModalError('');
                            }}
                            className="p-1.5 text-slate-500 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition inline-flex items-center"
                            title="Editar dados da matrícula e contrato"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          {!isProfessor && (
                            <button
                              onClick={() => handleDeleteEnrollment(enr)}
                              className="p-1.5 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded-lg transition inline-flex items-center"
                              title="Excluir matrícula"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
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

          {/* TAB 6: TURMAS & HORÁRIOS */}
          {activeTab === 'classes' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Grade de Turmas e Horários Semanais</h3>
                  <p className="text-xs text-slate-500">Capacidade configurável por sala e suporte a turmas mistas com múltiplos cursos no mesmo horário.</p>
                </div>
                {!isProfessor && (
                  <button
                    onClick={openNewClassModal}
                    className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
                  >
                    <Plus className="w-3.5 h-3.5" /> Nova Turma
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {classes.map((cls) => {
                  const enrolledNames = getTurmaStudents(cls.id);
                  const enrolledCount = enrolledNames.length;
                  const capMax = cls.capacidade_maxima || 1;
                  const isFull = enrolledCount >= capMax;
                  const cursosLista = Array.isArray(cls.cursos_nomes) && cls.cursos_nomes.length > 0
                    ? cls.cursos_nomes
                    : [cls.curso_nome || 'Artes'];

                  return (
                    <div key={cls.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 hover:border-amber-400 transition">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wide">
                            {cls.dia_semana} • {cls.turno} ({cls.horario_inicio} às {cls.horario_fim})
                          </span>
                          <h4 className="text-base font-bold text-slate-800 mt-1">{cls.nome}</h4>
                          <div className="flex flex-wrap items-center gap-1 mt-1">
                            {cursosLista.map((nomeCurso, idx) => (
                              <span key={idx} className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                {nomeCurso}
                              </span>
                            ))}
                            <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              cls.faixa_etaria
                                ? 'bg-slate-100 text-slate-700'
                                : 'bg-red-50 text-red-700 border border-red-200'
                            }`}>
                              {cls.faixa_etaria || 'Faixa etária não selecionada'}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                            isFull ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {enrolledCount} / {capMax} vagas
                          </span>
                          {!isProfessor && (
                            <>
                              <button
                                onClick={() => openEditClassModal(cls)}
                                className="p-1.5 text-slate-400 hover:text-amber-700 hover:bg-amber-50 rounded transition"
                                title="Editar turma"
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteClass(cls)}
                                className="p-1.5 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded transition"
                                title="Excluir ou desativar turma"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                        <span>Professor: <strong className="text-slate-700">{cls.professor_nome || 'Docente'}</strong></span>
                        <span>Sala: <strong className="text-slate-700">{cls.sala_nome || `Sala #${cls.sala_id}`}</strong></span>
                      </div>

                      <div className="mt-3">
                        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-2 rounded-full ${isFull ? 'bg-red-600' : 'bg-amber-600'}`}
                            style={{ width: `${Math.min(100, (enrolledCount / capMax) * 100)}%` }}
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

          {/* TAB 7: SALAS & CAPACIDADE */}
          {activeTab === 'rooms' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Estúdios de Criação e Salas de Aula</h3>
                  <p className="text-xs text-slate-500">Gerencie a infraestrutura física e configure a capacidade máxima de cada sala.</p>
                </div>
                {isAdminOrCoord && (
                  <button
                    onClick={() => {
                      setEditingRoom(null);
                      setShowRoomModal(true);
                    }}
                    className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
                  >
                    <Plus className="w-3.5 h-3.5" /> Nova Sala
                  </button>
                )}
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
                          <div className="flex items-center gap-1.5">
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">
                              Capacidade: {room.capacidade} alunos
                            </span>
                            {isAdminOrCoord && (
                              <>
                                <button
                                  onClick={() => {
                                    setEditingRoom(room);
                                    setShowRoomModal(true);
                                  }}
                                  className="p-1 text-slate-400 hover:text-amber-700 hover:bg-amber-50 rounded transition"
                                  title="Editar sala e capacidade"
                                >
                                  <Edit className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleDeleteRoom(room)}
                                  className="p-1 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded transition"
                                  title="Excluir ou desativar sala"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
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

          {/* TAB 8: FINANCEIRO & DRE */}
          {activeTab === 'financial' && (() => {
            const mesesNomes = [
              { id: '01', label: 'Janeiro' }, { id: '02', label: 'Fevereiro' }, { id: '03', label: 'Março' },
              { id: '04', label: 'Abril' }, { id: '05', label: 'Maio' }, { id: '06', label: 'Junho' },
              { id: '07', label: 'Julho' }, { id: '08', label: 'Agosto' }, { id: '09', label: 'Setembro' },
              { id: '10', label: 'Outubro' }, { id: '11', label: 'Novembro' }, { id: '12', label: 'Dezembro' },
            ];

            const getInvYearMonth = (item) => {
              if (item.competencia && item.competencia.includes('-')) {
                const [y, m] = item.competencia.split('-');
                return { y, m };
              }
              const parts = String(item.data_vencimento || '').split('T')[0].split('-');
              return { y: parts[0] || '', m: parts[1] || '' };
            };

            const currentYearStr = String(new Date().getFullYear());
            const yearsSet = new Set([currentYearStr]);
            invoices.forEach(inv => {
              const { y } = getInvYearMonth(inv);
              if (y) yearsSet.add(y);
            });
            const availableYears = Array.from(yearsSet).sort();

            const studentOptionsMap = new Map();
            students.forEach(s => {
              studentOptionsMap.set(String(s.id), {
                id: String(s.id),
                nome: s.nome,
                responsavel: s.responsavel?.nome || null,
              });
            });
            invoices.forEach(inv => {
              const sid = String(inv.aluno_id);
              if (!studentOptionsMap.has(sid)) {
                studentOptionsMap.set(sid, {
                  id: sid,
                  nome: inv.aluno_nome || `Aluno #${sid}`,
                  responsavel: inv.responsavel_nome || null,
                });
              } else if (!studentOptionsMap.get(sid).responsavel && inv.responsavel_nome) {
                studentOptionsMap.get(sid).responsavel = inv.responsavel_nome;
              }
            });
            const studentGuardianOptions = Array.from(studentOptionsMap.values()).sort((a, b) =>
              a.nome.localeCompare(b.nome, 'pt-BR')
            );

            const matchesCommonFilters = (item) => {
              const { y, m } = getInvYearMonth(item);
              if (invoiceYearFilter !== 'TODOS' && y !== invoiceYearFilter) return false;
              if (invoiceMonthFilter !== 'TODOS' && m !== invoiceMonthFilter) return false;
              if (invoiceStudentFilter !== 'TODOS' && String(item.aluno_id) !== invoiceStudentFilter) return false;
              if (invoiceSearch.trim()) {
                const q = invoiceSearch.toLowerCase();
                const matchAluno = item.aluno_nome?.toLowerCase().includes(q);
                const matchResp = item.responsavel_nome?.toLowerCase().includes(q);
                const matchDesc = item.descricao?.toLowerCase().includes(q);
                if (!matchAluno && !matchResp && !matchDesc) return false;
              }
              return true;
            };

            const baseFilteredInvoices = invoices.filter(matchesCommonFilters);
            const filteredInvoices = baseFilteredInvoices.filter(inv =>
              invoiceFilter === 'TODAS' ? inv.status !== 'CANCELADO' : inv.status === invoiceFilter
            );
            const filteredDefaulters = defaulters.filter(matchesCommonFilters);

            const totalFiltrado = filteredInvoices.reduce((acc, i) => acc + (i.valor_final || 0), 0);
            const totalPago = filteredInvoices.filter(i => i.status === 'PAGO').reduce((acc, i) => acc + (i.valor_final || 0), 0);
            const totalAberto = filteredInvoices.filter(i => i.status !== 'PAGO' && i.status !== 'CANCELADO').reduce((acc, i) => acc + (i.valor_final || 0), 0);
            const hasActiveFilters = invoiceFilter !== 'TODAS' || invoiceMonthFilter !== 'TODOS' || invoiceYearFilter !== 'TODOS' || invoiceStudentFilter !== 'TODOS' || invoiceSearch.trim() !== '';

            const activeDre = financialDre || dre;
            const dreMonthLabel = invoiceMonthFilter !== 'TODOS'
              ? mesesNomes.find(m => m.id === invoiceMonthFilter)?.label
              : null;
            const drePeriodLabel = dreMonthLabel && invoiceYearFilter !== 'TODOS'
              ? `${dreMonthLabel}/${invoiceYearFilter}`
              : dreMonthLabel
              ? `${dreMonthLabel}/${currentYearStr}`
              : invoiceYearFilter !== 'TODOS'
              ? `Ano ${invoiceYearFilter}`
              : 'Mês Corrente';

            return (
            <div className="space-y-6">
              {/* DRE do Período */}
              {activeDre && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                    <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-emerald-600" />
                      DRE Operacional — {drePeriodLabel}
                      {invoiceStudentFilter !== 'TODOS' && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                          Aluno: {studentOptionsMap.get(invoiceStudentFilter)?.nome}
                        </span>
                      )}
                    </h3>
                    <span className="text-xs text-slate-400">
                      Período: {formatDateBR(activeDre.competencia_inicio)} até {formatDateBR(activeDre.competencia_fim)}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <span className="text-[11px] text-slate-500 font-semibold uppercase block">Receita Bruta</span>
                      <span className="text-base font-bold text-slate-800">R$ {Number(activeDre.receita_bruta || 0).toFixed(2)}</span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <span className="text-[11px] text-slate-500 font-semibold uppercase block">Descontos</span>
                      <span className="text-base font-bold text-amber-700">- R$ {Number(activeDre.deducoes_descontos || 0).toFixed(2)}</span>
                    </div>
                    <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100">
                      <span className="text-[11px] text-emerald-700 font-semibold uppercase block">Receita Líquida</span>
                      <span className="text-base font-bold text-emerald-700">R$ {Number(activeDre.receita_liquida || 0).toFixed(2)}</span>
                    </div>
                    <div className="p-3 bg-red-50/50 rounded-lg border border-red-100">
                      <span className="text-[11px] text-red-700 font-semibold uppercase block">Despesas Op.</span>
                      <span className="text-base font-bold text-red-600">
                        {invoiceStudentFilter !== 'TODOS' ? '—' : `- R$ ${Number(activeDre.despesas_operacionais || 0).toFixed(2)}`}
                      </span>
                    </div>
                    <div className="p-3 bg-slate-900 rounded-lg text-white col-span-2 md:col-span-1">
                      <span className="text-[11px] text-slate-300 font-semibold uppercase block">Resultado Líquido</span>
                      <span className="text-base font-bold text-emerald-400">R$ {Number(activeDre.resultado_liquido || 0).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Inadimplentes */}
              {filteredDefaulters.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-red-800 text-base flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                      Régua de Cobrança — Títulos Inadimplentes ({filteredDefaulters.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {filteredDefaulters.map((def) => (
                      <div key={def.id} className="bg-white p-4 rounded-lg border border-red-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <span className="font-semibold text-slate-800">{def.aluno_nome}</span>
                          {def.responsavel_nome && (
                            <span className="text-xs text-slate-500 ml-2">(Resp: {def.responsavel_nome})</span>
                          )}
                          <span className="text-xs text-slate-500 block">Vencido em: {formatDateBR(def.data_vencimento)} • {def.descricao}</span>
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
                <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">Mensalidades e Títulos Financeiros</h3>
                    <p className="text-xs text-slate-500">Formas homologadas: PIX, Cartão, Boleto e Dinheiro. Receba mensalidades com baixa imediata.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleSyncAllInvoices}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow-sm"
                      title="Gerar parcelas pendentes de todas as matrículas ativas"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Gerar / Sincronizar Parcelas
                    </button>
                    <a
                      href={api.exportInvoicesUrl}
                      className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" /> Exportar CSV
                    </a>
                  </div>
                </div>

                {/* Filtros por Mês, Ano, Aluno & Responsável, Status e Busca */}
                <div className="p-4 bg-slate-50 border-b border-slate-200 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-500 mb-1">Mês de Competência</label>
                      <select
                        value={invoiceMonthFilter}
                        onChange={(e) => setInvoiceMonthFilter(e.target.value)}
                        className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:border-amber-500"
                      >
                        <option value="TODOS">Todos os meses</option>
                        {mesesNomes.map(m => (
                          <option key={m.id} value={m.id}>{m.label}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-500 mb-1">Ano</label>
                      <select
                        value={invoiceYearFilter}
                        onChange={(e) => setInvoiceYearFilter(e.target.value)}
                        className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:border-amber-500"
                      >
                        <option value="TODOS">Todos os anos</option>
                        {availableYears.map(y => (
                          <option key={y} value={y}>{y}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-500 mb-1">Aluno & Responsável</label>
                      <select
                        value={invoiceStudentFilter}
                        onChange={(e) => setInvoiceStudentFilter(e.target.value)}
                        className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:border-amber-500"
                      >
                        <option value="TODOS">Todos os alunos e responsáveis</option>
                        {studentGuardianOptions.map(opt => (
                          <option key={opt.id} value={opt.id}>
                            {opt.nome}{opt.responsavel ? ` (Resp: ${opt.responsavel})` : ''}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-500 mb-1">Busca Rápida</label>
                      <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-2 text-slate-400" />
                        <input
                          type="text"
                          value={invoiceSearch}
                          onChange={(e) => setInvoiceSearch(e.target.value)}
                          placeholder="Aluno, responsável ou descrição..."
                          className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:border-amber-500"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { id: 'TODAS', label: `Todas (${baseFilteredInvoices.filter(i => i.status !== 'CANCELADO').length})` },
                        { id: 'PENDENTE', label: `Pendentes (${baseFilteredInvoices.filter(i => i.status === 'PENDENTE').length})` },
                        { id: 'ATRASADO', label: `Vencidas (${baseFilteredInvoices.filter(i => i.status === 'ATRASADO').length})` },
                        { id: 'PAGO', label: `Pagas (${baseFilteredInvoices.filter(i => i.status === 'PAGO').length})` },
                        { id: 'CANCELADO', label: `Canceladas (${baseFilteredInvoices.filter(i => i.status === 'CANCELADO').length})` },
                      ].map(f => (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => setInvoiceFilter(f.id)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                            invoiceFilter === f.id
                              ? 'bg-amber-700 text-white shadow-sm'
                              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                          }`}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs">
                      <span className="text-slate-600">
                        Total filtrado: <strong className="text-slate-900">R$ {totalFiltrado.toFixed(2)}</strong>
                      </span>
                      <span className="text-emerald-700">
                        Pago: <strong>R$ {totalPago.toFixed(2)}</strong>
                      </span>
                      <span className="text-amber-700">
                        Em aberto: <strong>R$ {totalAberto.toFixed(2)}</strong>
                      </span>
                      {hasActiveFilters && (
                        <button
                          type="button"
                          onClick={() => {
                            setInvoiceFilter('TODAS');
                            setInvoiceMonthFilter('TODOS');
                            setInvoiceYearFilter('TODOS');
                            setInvoiceStudentFilter('TODOS');
                            setInvoiceSearch('');
                          }}
                          className="px-2.5 py-1 text-[11px] font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-100 rounded-lg transition"
                        >
                          Limpar filtros
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-600">
                    <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3">Descrição / Parcela</th>
                        <th className="px-6 py-3">Aluno & Responsável</th>
                        <th className="px-6 py-3">Vencimento</th>
                        <th className="px-6 py-3">Valor</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-right">Ação</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredInvoices.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-6 py-10 text-center text-xs text-slate-400">
                            Nenhuma mensalidade encontrada para os filtros selecionados. Caso haja matrículas ativas sem parcelas, clique em <strong>Gerar / Sincronizar Parcelas</strong> acima.
                          </td>
                        </tr>
                      ) : filteredInvoices.map((inv) => (
                        <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                          <td className="px-6 py-4 font-medium text-slate-900">
                            <div>{inv.descricao}</div>
                            <span className="text-[11px] text-slate-400">Competência: {inv.competencia}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-medium text-slate-800 block">{inv.aluno_nome || 'Aluno'}</span>
                            {inv.responsavel_nome && (
                              <span className="text-[11px] text-slate-400 block">Resp: {inv.responsavel_nome}</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-xs">
                            <span className={inv.status === 'ATRASADO' ? 'text-red-600 font-bold' : ''}>
                              {formatDateBR(inv.data_vencimento)}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-bold text-slate-800 block">R$ {inv.valor_final.toFixed(2)}</span>
                            {inv.desconto_aplicado > 0 && (
                              <span className="text-[11px] text-emerald-600 block">Desc: R$ {inv.desconto_aplicado.toFixed(2)}</span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                              inv.status === 'PAGO' ? 'bg-emerald-100 text-emerald-800' :
                              inv.status === 'ATRASADO' ? 'bg-red-100 text-red-800' :
                              inv.status === 'CANCELADO' ? 'bg-slate-200 text-slate-600' : 'bg-amber-100 text-amber-800'
                            }`}>
                              {inv.status === 'PAGO' ? '✓ PAGO' : inv.status === 'ATRASADO' ? '⚠ VENCIDO' : inv.status === 'CANCELADO' ? '✕ CANCELADO' : '⏳ PENDENTE'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            {inv.status === 'PAGO' ? (
                              <span className="text-xs text-emerald-700 font-medium inline-flex items-center gap-1">
                                <Check className="w-3.5 h-3.5" /> Pago ({inv.forma_pagamento || 'OK'})
                              </span>
                            ) : inv.status === 'CANCELADO' ? (
                              <span className="text-xs text-slate-400 font-medium">Cancelada</span>
                            ) : (
                              <button
                                onClick={() => {
                                  setShowPayModal(inv);
                                  setPayValue(inv.valor_final);
                                  setModalError('');
                                }}
                                className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition inline-flex items-center gap-1 shadow-sm"
                                title="Receber mensalidade e dar baixa"
                              >
                                <CreditCard className="w-3.5 h-3.5" /> Receber / Baixa
                              </button>
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
          })()}

          {/* TAB 9: FREQUÊNCIA & DIÁRIO DE CLASSE */}
          {activeTab === 'attendance' && (
            <div className="space-y-6">
              {/* Sub-navegação da Frequência */}
              <div className="flex border-b border-slate-200 gap-2 overflow-x-auto">
                <button
                  type="button"
                  onClick={() => setAttendanceSubTab('chamada')}
                  className={`pb-3 px-4 text-xs font-bold transition border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    attendanceSubTab === 'chamada'
                      ? 'border-amber-700 text-amber-900'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Calendar className="w-4 h-4" /> Lançar Diário & Presença
                </button>
                <button
                  type="button"
                  onClick={() => setAttendanceSubTab('turmas')}
                  className={`pb-3 px-4 text-xs font-bold transition border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    attendanceSubTab === 'turmas'
                      ? 'border-amber-700 text-amber-900'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <BarChart2 className="w-4 h-4" /> Relatório Geral por Turmas
                </button>
                <button
                  type="button"
                  onClick={() => setAttendanceSubTab('aluno')}
                  className={`pb-3 px-4 text-xs font-bold transition border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    attendanceSubTab === 'aluno'
                      ? 'border-amber-700 text-amber-900'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Users className="w-4 h-4" /> Frequência por Aluno
                </button>
              </div>

              {/* Sub-tab 1: Lançar Diário & Presença */}
              {attendanceSubTab === 'chamada' && (
                <>
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
                              <span className="text-slate-500">Data: {formatDateBR(l.data_aula)} • {l.materiais_utilizados || 'Sem materiais'}</span>
                            </div>
                            <span className="px-2 py-1 rounded bg-slate-200 text-slate-700 font-semibold">Registrada</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Sub-tab 2: Visão Geral por Turmas */}
              {attendanceSubTab === 'turmas' && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">Visão Geral de Presenças por Turma</h3>
                    <p className="text-xs text-slate-500">Métricas de frequência acumuladas e taxa de engajamento dos alunos por modalidade.</p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-600">
                      <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-y border-slate-100">
                        <tr>
                          <th className="px-4 py-3">Turma / Modalidade</th>
                          <th className="px-4 py-3">Professor</th>
                          <th className="px-4 py-3">Horário</th>
                          <th className="px-4 py-3 text-center">Matriculados</th>
                          <th className="px-4 py-3 text-center">Aulas Registradas</th>
                          <th className="px-4 py-3 text-center">Presenças</th>
                          <th className="px-4 py-3 text-center">Faltas</th>
                          <th className="px-4 py-3">Taxa de Presença</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {attendanceClassesSummary.length === 0 ? (
                          <tr>
                            <td colSpan="8" className="px-4 py-6 text-center text-slate-400">Nenhum registro de aula computado ainda.</td>
                          </tr>
                        ) : (
                          attendanceClassesSummary.map((item) => (
                            <tr key={item.turma_id} className="hover:bg-slate-50">
                              <td className="px-4 py-3 font-semibold text-slate-800">
                                <div>{item.turma_nome}</div>
                                <span className="text-[11px] text-slate-400 font-normal">{item.curso_nome}</span>
                              </td>
                              <td className="px-4 py-3">{item.professor_nome}</td>
                              <td className="px-4 py-3">{item.dia_semana ? `${item.dia_semana} • ${item.horario}` : 'Regular'}</td>
                              <td className="px-4 py-3 text-center">
                                <span className="font-semibold text-slate-700">{item.total_matriculados ?? '—'}</span> / {item.capacidade_maxima ?? '—'}
                              </td>
                              <td className="px-4 py-3 text-center font-bold text-slate-700">{item.total_aulas_registradas ?? item.total_aulas ?? 0}</td>
                              <td className="px-4 py-3 text-center text-emerald-700 font-semibold">{item.total_presencas}</td>
                              <td className="px-4 py-3 text-center text-red-600 font-semibold">{item.total_faltas}</td>
                              <td className="px-4 py-3 min-w-[150px]">
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                                    <div
                                      className={`h-2 rounded-full ${
                                        item.taxa_presenca_percentual >= 75
                                          ? 'bg-emerald-500'
                                          : item.taxa_presenca_percentual >= 50
                                          ? 'bg-amber-500'
                                          : 'bg-red-500'
                                      }`}
                                      style={{ width: `${Math.min(100, item.taxa_presenca_percentual)}%` }}
                                    ></div>
                                  </div>
                                  <span className="font-bold text-xs text-slate-700 min-w-[42px] text-right">
                                    {item.taxa_presenca_percentual}%
                                  </span>
                                </div>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Sub-tab 3: Frequência por Aluno */}
              {attendanceSubTab === 'aluno' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                    <h3 className="font-bold text-slate-800 text-lg mb-1">Histórico Individual de Presenças</h3>
                    <p className="text-xs text-slate-500 mb-4">Consulte o histórico detalhado de chamadas, ausências justificadas e taxa de frequência de qualquer aluno.</p>
                    <div className="max-w-md">
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Selecione o Aluno</label>
                      <select
                        value={selectedStudentForHistory}
                        onChange={(e) => setSelectedStudentForHistory(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                      >
                        <option value="">-- Escolha um aluno para analisar --</option>
                        {students.map((st) => (
                          <option key={st.id} value={st.id}>
                            {st.nome}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {loadingStudentHistory && (
                    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 text-center text-xs text-slate-500">
                      Carregando histórico de frequência do aluno...
                    </div>
                  )}

                  {!loadingStudentHistory && studentAttendanceHistory && (() => {
                    const records = studentAttendanceHistory.registros || studentAttendanceHistory.historico || [];
                    const justificadas = studentAttendanceHistory.total_justificadas ?? studentAttendanceHistory.total_faltas_justificadas ?? 0;

                    return (
                      <div className="space-y-6">
                        {/* Cartões de Métricas do Aluno */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                            <span className="text-xs text-slate-400 block font-medium">Total de Aulas</span>
                            <span className="text-2xl font-bold text-slate-800 mt-1 block">{studentAttendanceHistory.total_aulas ?? 0}</span>
                          </div>
                          <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200/60 shadow-sm">
                            <span className="text-xs text-emerald-800 block font-medium">Presenças</span>
                            <span className="text-2xl font-bold text-emerald-900 mt-1 block">{studentAttendanceHistory.total_presencas ?? 0}</span>
                          </div>
                          <div className="bg-red-50/70 p-4 rounded-xl border border-red-200/60 shadow-sm">
                            <span className="text-xs text-red-800 block font-medium">Faltas</span>
                            <span className="text-2xl font-bold text-red-900 mt-1 block">{studentAttendanceHistory.total_faltas ?? 0}</span>
                            {justificadas > 0 && (
                              <span className="text-[11px] text-amber-700 font-medium">
                                ({justificadas} justificadas)
                              </span>
                            )}
                          </div>
                          <div className="bg-amber-50/70 p-4 rounded-xl border border-amber-200/60 shadow-sm">
                            <span className="text-xs text-amber-800 block font-medium">Taxa de Frequência</span>
                            <span className="text-2xl font-bold text-amber-900 mt-1 block">{studentAttendanceHistory.taxa_presenca_percentual ?? 100}%</span>
                          </div>
                        </div>

                        {/* Lista cronológica de aulas do aluno */}
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                          <h4 className="font-bold text-slate-800 text-sm mb-4">Registro de Frequência em Aulas</h4>
                          {records.length === 0 ? (
                            <p className="text-xs text-slate-400 italic">Nenhum registro de chamada encontrado para este aluno.</p>
                          ) : (
                            <div className="overflow-x-auto">
                              <table className="w-full text-left text-xs text-slate-600">
                                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-y border-slate-100">
                                  <tr>
                                    <th className="px-4 py-3">Data</th>
                                    <th className="px-4 py-3">Turma</th>
                                    <th className="px-4 py-3">Tema da Aula</th>
                                    <th className="px-4 py-3">Status</th>
                                    <th className="px-4 py-3">Observações</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {records.map((rec, idx) => (
                                    <tr key={idx} className="hover:bg-slate-50">
                                      <td className="px-4 py-3 whitespace-nowrap font-medium text-slate-800">
                                        {rec.data_aula ? formatDateBR(rec.data_aula) : '—'}
                                      </td>
                                      <td className="px-4 py-3 whitespace-nowrap">{rec.turma_nome}</td>
                                      <td className="px-4 py-3 font-medium text-slate-700">{rec.tema_aula || '—'}</td>
                                      <td className="px-4 py-3 whitespace-nowrap">
                                        <span
                                          className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                                            rec.status === 'PRESENTE'
                                              ? 'bg-emerald-100 text-emerald-800'
                                              : rec.status === 'JUSTIFICADA'
                                              ? 'bg-amber-100 text-amber-800'
                                              : 'bg-red-100 text-red-800'
                                          }`}
                                        >
                                          {rec.status}
                                        </span>
                                      </td>
                                      <td className="px-4 py-3 text-slate-500">{rec.motivo_justificativa || rec.observacao || '—'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          )}

          {/* TAB 10: BACKUPS */}
          {activeTab === 'backups' && (
            <div className="space-y-6">
              {/* Backups Locais */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">Backups Locais do Banco de Dados SQLite</h3>
                    <p className="text-xs text-slate-500">Snapshots atômicos armazenados no servidor local para recuperação rápida ou cópia em pendrive.</p>
                  </div>
                  <div className="flex flex-wrap gap-2 self-start sm:self-auto">
                    <button
                      onClick={handleBackup}
                      disabled={remoteBusy}
                      className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow disabled:opacity-50"
                    >
                      <HardDrive className="w-4 h-4" /> Criar Snapshot Agora
                    </button>
                    {remoteBackupStatus?.configurado && (
                      <button
                        onClick={handleSyncRemoteNow}
                        disabled={remoteBusy}
                        className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition flex items-center gap-1.5 shadow disabled:opacity-50"
                      >
                        <Cloud className="w-4 h-4" /> Gerar e Enviar p/ Supabase
                      </button>
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  {backups.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">Nenhum snapshot local gerado ainda.</p>
                  ) : backups.map((b, i) => (
                    <div key={i} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-800 text-sm">{b.arquivo}</p>
                        <span className="text-xs text-slate-400">Criado em: {new Date(b.criado_em).toLocaleString('pt-BR')}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-1 rounded">{b.tamanho_formatado}</span>
                        {remoteBackupStatus?.configurado && (
                          <button
                            onClick={() => handleUploadToRemote(b.arquivo)}
                            disabled={remoteBusy}
                            className="px-2.5 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 rounded-lg transition inline-flex items-center gap-1 disabled:opacity-50"
                            title="Enviar este snapshot para o Supabase"
                          >
                            <Upload className="w-3.5 h-3.5" /> Enviar p/ Nuvem
                          </button>
                        )}
                        <button
                          onClick={() => handleDownloadLocalBackup(b.arquivo)}
                          className="p-2 text-slate-600 hover:text-amber-800 bg-white border border-slate-200 rounded-lg transition"
                          title="Download para pendrive"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Backup Remoto em Nuvem (Supabase Storage) */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6 space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                  <div>
                    <div className="flex items-center gap-2">
                      <Cloud className="w-5 h-5 text-emerald-600" />
                      <h3 className="font-bold text-slate-800 text-lg">Backup Remoto em Nuvem (Supabase Storage)</h3>
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        remoteBackupStatus?.configurado ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {remoteBackupStatus?.configurado ? '✓ Conectado' : 'Não configurado'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Envie cópias criptografadas em trânsito para um bucket privado no Supabase para proteção contra falhas físicas no computador local.
                    </p>
                  </div>
                  {remoteBackupStatus?.configurado && (
                    <button
                      type="button"
                      onClick={handleTestRemoteBackup}
                      disabled={remoteBusy}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition inline-flex items-center gap-1.5 self-start sm:self-auto disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${remoteBusy ? 'animate-spin' : ''}`} /> Testar Conexão
                    </button>
                  )}
                </div>

                {/* Formulário de Configuração do Supabase */}
                <form onSubmit={handleSaveRemoteConfig} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">URL do Projeto Supabase</label>
                      <input
                        type="url"
                        required
                        placeholder="https://seu-projeto.supabase.co"
                        value={remoteConfigForm.supabase_url}
                        onChange={(e) => setRemoteConfigForm(prev => ({ ...prev, supabase_url: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg text-xs bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">
                        Service Role Key {remoteBackupStatus?.chave_mascarada ? `(Atual: ${remoteBackupStatus.chave_mascarada})` : ''}
                      </label>
                      <input
                        type="password"
                        required={!remoteBackupStatus?.configurado}
                        placeholder={remoteBackupStatus?.configurado ? 'Deixe em branco para manter a chave atual' : 'eyJhbGciOi... (service_role)'}
                        value={remoteConfigForm.service_role_key}
                        onChange={(e) => setRemoteConfigForm(prev => ({ ...prev, service_role_key: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg text-xs bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Bucket Privado</label>
                      <input
                        type="text"
                        required
                        value={remoteConfigForm.bucket}
                        onChange={(e) => setRemoteConfigForm(prev => ({ ...prev, bucket: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg text-xs bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Pasta / Prefixo</label>
                      <input
                        type="text"
                        value={remoteConfigForm.prefixo}
                        onChange={(e) => setRemoteConfigForm(prev => ({ ...prev, prefixo: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg text-xs bg-white outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <label className="inline-flex items-center gap-2 text-xs text-slate-700 font-medium cursor-pointer">
                      <input
                        type="checkbox"
                        checked={remoteConfigForm.auto_enviar_ao_criar}
                        onChange={(e) => setRemoteConfigForm(prev => ({ ...prev, auto_enviar_ao_criar: e.target.checked }))}
                        className="rounded text-emerald-600"
                      />
                      Enviar automaticamente para o Supabase sempre que um snapshot local for criado
                    </label>
                    <button
                      type="submit"
                      disabled={remoteBusy}
                      className="px-4 py-2 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-900 rounded-lg transition self-start sm:self-auto disabled:opacity-50"
                    >
                      {remoteBusy ? 'Validando...' : 'Salvar e Validar Supabase'}
                    </button>
                  </div>
                </form>

                {/* Lista de Backups no Supabase */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Snapshots Armazenados na Nuvem ({remoteBackups.length})
                  </h4>
                  {!remoteBackupStatus?.configurado ? (
                    <p className="text-xs text-slate-400 italic py-2">
                      Configure a URL e a Service Role Key do Supabase acima (ou via variáveis de ambiente) para habilitar o armazenamento remoto.
                    </p>
                  ) : remoteBackups.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-2">
                      Nenhum snapshot encontrado no bucket '{remoteBackupStatus.bucket}'. Clique em "Gerar e Enviar p/ Supabase" ou envie um backup local acima.
                    </p>
                  ) : (
                    remoteBackups.map((rb, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-emerald-100 bg-emerald-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-slate-800 text-sm">{rb.arquivo}</p>
                          <span className="text-xs text-slate-500 block">
                            Caminho: {rb.caminho_remoto}
                            {rb.criado_em ? ` • Enviado em: ${new Date(rb.criado_em).toLocaleString('pt-BR')}` : ''}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-emerald-800 bg-emerald-100 px-2 py-1 rounded">{rb.tamanho_formatado}</span>
                          <button
                            onClick={() => handlePullFromRemote(rb.arquivo)}
                            disabled={remoteBusy}
                            className="px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 rounded-lg transition disabled:opacity-50"
                            title="Copiar snapshot do Supabase para backups locais"
                          >
                            Copiar p/ Local
                          </button>
                          <button
                            onClick={() => handleDownloadRemoteBackup(rb.arquivo)}
                            className="p-2 text-slate-600 hover:text-emerald-700 bg-white border border-slate-200 rounded-lg transition"
                            title="Baixar snapshot da nuvem"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteRemoteBackup(rb.arquivo)}
                            disabled={remoteBusy}
                            className="p-2 text-slate-500 hover:text-red-600 bg-white border border-slate-200 rounded-lg transition disabled:opacity-50"
                            title="Excluir snapshot remoto"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 11: GESTÃO DE USUÁRIOS & ACESSOS (RBAC) */}
          {activeTab === 'users' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">Usuários & Controle de Acesso (RBAC)</h3>
                    <p className="text-xs text-slate-500">
                      Gerencie acessos e vincule professores para que cada um acesse somente suas próprias turmas e diários.
                    </p>
                  </div>
                  {isAdminOrCoord && (
                    <button
                      onClick={() => {
                        setEditingUser(null);
                        setUserFormRole('Direção');
                        setModalError('');
                        setShowUserModal(true);
                      }}
                      className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg transition flex items-center gap-1.5 shadow self-start sm:self-auto"
                    >
                      <Plus className="w-4 h-4" /> Novo Usuário
                    </button>
                  )}
                </div>

                <div className="overflow-x-auto mt-4">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-y border-slate-100">
                      <tr>
                        <th className="px-6 py-3">Usuário</th>
                        <th className="px-6 py-3">Perfil de Acesso</th>
                        <th className="px-6 py-3">Vínculo Docente</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {users.length === 0 ? (
                        <tr>
                          <td colSpan="5" className="px-6 py-6 text-center text-slate-400">
                            Nenhum usuário cadastrado.
                          </td>
                        </tr>
                      ) : (
                        users.map((usr) => {
                          const linkedTeacher = teachers.find(t => t.id === usr.professor_id);
                          return (
                            <tr key={usr.id} className="hover:bg-slate-50">
                              <td className="px-6 py-4">
                                <div className="font-semibold text-slate-900">{usr.nome}</div>
                                <div className="text-slate-400 text-[11px]">{usr.email}</div>
                              </td>
                              <td className="px-6 py-4">
                                <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                                  (usr.role === 'DIRECAO' || usr.role === 'Direção')
                                    ? 'bg-purple-100 text-purple-800'
                                    : (usr.role === 'COORDENACAO' || usr.role === 'Coordenação')
                                    ? 'bg-blue-100 text-blue-800'
                                    : (usr.role === 'Professor' || usr.role === 'PROFESSOR')
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-emerald-100 text-emerald-800'
                                }`}>
                                  {usr.role}
                                </span>
                              </td>
                              <td className="px-6 py-4">
                                {(usr.role === 'Professor' || usr.role === 'PROFESSOR') ? (
                                  linkedTeacher ? (
                                    <span className="font-medium text-slate-700 flex items-center gap-1">
                                      <UserCheck className="w-3.5 h-3.5 text-emerald-600" /> {linkedTeacher.nome}
                                    </span>
                                  ) : (
                                    <span className="text-amber-700 text-xs italic">Não vinculado</span>
                                  )
                                ) : (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="px-6 py-4">
                                <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                  usr.ativo ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                                }`}>
                                  {usr.ativo ? 'Ativo' : 'Inativo'}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-right space-x-2">
                                {isAdminOrCoord && (
                                  <>
                                    <button
                                      onClick={() => {
                                        setEditingUser(usr);
                                        setUserFormRole(usr.role || 'Direção');
                                        setModalError('');
                                        setShowUserModal(true);
                                      }}
                                      className="p-1.5 text-slate-500 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition inline-flex items-center"
                                      title="Editar Usuário"
                                    >
                                      <Edit className="w-4 h-4" />
                                    </button>
                                    <button
                                      onClick={() => handleToggleUserStatus(usr)}
                                      className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                                        usr.ativo
                                          ? 'border border-red-200 text-red-600 hover:bg-red-50'
                                          : 'border border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                                      }`}
                                      title={usr.ativo ? 'Desativar acesso' : 'Ativar acesso'}
                                    >
                                      {usr.ativo ? 'Desativar' : 'Ativar'}
                                    </button>
                                  </>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* MODAL: NOVO / EDITAR ALUNO */}
      {showStudentModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">
                {editingStudent ? 'Editar Aluno & Responsável' : 'Novo Aluno'}
              </h3>
              <button
                onClick={() => {
                  setShowStudentModal(false);
                  setEditingStudent(null);
                  setModalError('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSaveStudent} className="space-y-4 mt-4">
              {modalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                  {modalError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome Completo</label>
                <input
                  name="nome"
                  required
                  defaultValue={editingStudent?.nome || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Nascimento</label>
                  <input
                    name="data_nascimento"
                    type="date"
                    required
                    defaultValue={editingStudent?.data_nascimento || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">CPF (Adultos)</label>
                  <input
                    name="cpf"
                    placeholder="000.000.000-00"
                    defaultValue={editingStudent?.cpf || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Telefone / WhatsApp</label>
                  <input
                    name="telefone"
                    placeholder="(19) 9..."
                    defaultValue={editingStudent?.telefone || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">E-mail</label>
                  <input
                    name="email"
                    type="email"
                    placeholder="aluno@email.com"
                    defaultValue={editingStudent?.email || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Endereço Residencial</label>
                <input
                  name="endereco"
                  placeholder="Rua, número, bairro..."
                  defaultValue={editingStudent?.endereco || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Alergias ou Observações de Saúde</label>
                <input
                  name="alergias"
                  placeholder="Tinta acrílica, poeira..."
                  defaultValue={editingStudent?.alergias || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              {/* Seção Responsável Legal (Para menores) */}
              <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl space-y-3">
                <span className="text-xs font-bold text-amber-900 block">Responsável Legal & Financeiro (Obrigatório para menores)</span>
                <div>
                  <input
                    name="resp_nome"
                    placeholder="Nome do Responsável Legal"
                    defaultValue={editingStudent?.responsavel?.nome || ''}
                    className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    name="resp_cpf"
                    placeholder="CPF: 000.000.000-00"
                    defaultValue={editingStudent?.responsavel?.cpf || ''}
                    className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white"
                  />
                  <input
                    name="resp_telefone"
                    placeholder="Telefone: (19) 9..."
                    defaultValue={editingStudent?.responsavel?.telefone || ''}
                    className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white"
                  />
                </div>
                <input
                  name="resp_email"
                  placeholder="E-mail do responsável"
                  defaultValue={editingStudent?.responsavel?.email || ''}
                  className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white"
                />
                <input
                  name="resp_endereco"
                  placeholder="Endereço residencial"
                  defaultValue={editingStudent?.responsavel?.endereco || ''}
                  className="w-full px-3 py-1.5 border rounded-lg text-xs bg-white"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  name="autorizacao_imagem"
                  type="checkbox"
                  id="auth_img"
                  defaultChecked={editingStudent ? editingStudent.autorizacao_imagem : false}
                  className="rounded text-amber-600"
                />
                <label htmlFor="auth_img" className="text-xs text-slate-600">Autorizo uso de imagem em redes sociais e eventos</label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setShowStudentModal(false);
                    setEditingStudent(null);
                    setModalError('');
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow"
                >
                  {editingStudent ? 'Salvar Alterações' : 'Salvar Aluno'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: NOVO CURSO / MODALIDADE ARTÍSTICA */}
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

      {/* MODAL: EDITAR CURSO */}
      {editingCourse && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Editar Modalidade Artística</h3>
              <button onClick={() => setEditingCourse(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleUpdateCourse} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome do Curso / Modalidade</label>
                <input
                  name="nome"
                  required
                  defaultValue={editingCourse.nome}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Descrição</label>
                <textarea
                  name="descricao"
                  rows="3"
                  defaultValue={editingCourse.descricao || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                ></textarea>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Duração (Meses)</label>
                  <input
                    name="duracao_meses"
                    type="number"
                    defaultValue={editingCourse.duracao_meses}
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
                    defaultValue={editingCourse.valor_mensalidade}
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800 outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  name="ativo"
                  type="checkbox"
                  id="course_active"
                  defaultChecked={editingCourse.ativo}
                  className="rounded text-amber-600"
                />
                <label htmlFor="course_active" className="text-xs text-slate-700 font-medium">Modalidade Ativa no Catálogo</label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setEditingCourse(null)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Salvar Alterações</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: NOVO PROFESSOR */}
      {showTeacherModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Cadastrar Novo Professor</h3>
              <button onClick={() => setShowTeacherModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTeacher} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome Completo</label>
                <input
                  name="nome"
                  required
                  placeholder="Ex: Prof. Helena Barufaldi"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">E-mail Profissional</label>
                  <input
                    name="email"
                    type="email"
                    required
                    placeholder="professor@hbartes.com"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Telefone / WhatsApp</label>
                  <input
                    name="telefone"
                    placeholder="(19) 99999-9999"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Especialidades Artísticas</label>
                <input
                  name="especialidades"
                  placeholder="Ex: Desenho Artístico, Aquarela, Óleo sobre Tela, Mangá"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Disponibilidade de Dias/Horários</label>
                  <input
                    name="disponibilidade"
                    placeholder="Ex: Segundas e Terças - Tarde"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Professor Substituto Preferencial</label>
                  <select
                    name="substituto_id"
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="">-- Nenhum substituto --</option>
                    {teachers.map(t => (
                      <option key={t.id} value={t.id}>{t.nome}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Endereço Residencial (Opcional)</label>
                <input
                  name="endereco"
                  placeholder="Rua, número, bairro, cidade"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowTeacherModal(false)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Salvar Professor</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EDITAR PROFESSOR */}
      {editingTeacher && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Editar Professor(a)</h3>
              <button onClick={() => setEditingTeacher(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleUpdateTeacher} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome Completo</label>
                <input
                  name="nome"
                  required
                  defaultValue={editingTeacher.nome}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">E-mail Profissional</label>
                  <input
                    name="email"
                    type="email"
                    required
                    defaultValue={editingTeacher.email}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Telefone / WhatsApp</label>
                  <input
                    name="telefone"
                    defaultValue={editingTeacher.telefone || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Especialidades Artísticas</label>
                <input
                  name="especialidades"
                  defaultValue={editingTeacher.especialidades || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Disponibilidade</label>
                  <input
                    name="disponibilidade"
                    defaultValue={editingTeacher.disponibilidade || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Substituto Preferencial</label>
                  <select
                    name="substituto_id"
                    defaultValue={editingTeacher.substituto_id || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="">-- Nenhum substituto --</option>
                    {teachers.filter(t => t.id !== editingTeacher.id).map(t => (
                      <option key={t.id} value={t.id}>{t.nome}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Endereço Residencial</label>
                <input
                  name="endereco"
                  defaultValue={editingTeacher.endereco || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  name="ativo"
                  type="checkbox"
                  id="teacher_active"
                  defaultChecked={editingTeacher.ativo}
                  className="rounded text-amber-600"
                />
                <label htmlFor="teacher_active" className="text-xs text-slate-700 font-medium">Professor Ativo no Corpo Docente</label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setEditingTeacher(null)} className="px-4 py-2 text-xs font-semibold text-slate-600">Cancelar</button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">Salvar Alterações</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: MATRICULAR ALUNO EM CURSO / TURMA */}
      {showEnrollmentModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Matricular Aluno em Curso / Turma</h3>
              <button
                onClick={() => {
                  setShowEnrollmentModal(false);
                  setModalError('');
                  setEnrollSelectedTurmaId('');
                  setEnrollSelectedCursoId('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateEnrollment} className="space-y-4 mt-4">
              {modalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                  {modalError}
                </div>
              )}

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
                <label className="block text-xs font-semibold text-slate-600 mb-1">Selecione a Turma</label>
                <select
                  name="turma_id"
                  required
                  value={enrollSelectedTurmaId}
                  onChange={(e) => {
                    const turmaVal = e.target.value;
                    setEnrollSelectedTurmaId(turmaVal);
                    const selTurma = classes.find(c => c.id === parseInt(turmaVal, 10));
                    if (selTurma) {
                      const turmaCursos = Array.isArray(selTurma.cursos) && selTurma.cursos.length > 0
                        ? selTurma.cursos
                        : courses.filter(cr => cr.id === selTurma.curso_id);
                      const firstCurso = turmaCursos[0];
                      setEnrollSelectedCursoId(firstCurso ? String(firstCurso.id) : '');
                      const fullCourse = firstCurso ? courses.find(cr => cr.id === firstCurso.id) : null;
                      const valMensal = fullCourse?.valor_mensalidade ?? firstCurso?.valor_mensalidade;
                      if (valMensal != null) {
                        const valInput = document.getElementById('enroll_valor_mensalidade');
                        if (valInput) valInput.value = Number(valMensal).toFixed(2);
                      }
                    } else {
                      setEnrollSelectedCursoId('');
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

              {(() => {
                const selTurma = classes.find(c => c.id === parseInt(enrollSelectedTurmaId, 10));
                if (!selTurma) return null;
                const turmaCursos = Array.isArray(selTurma.cursos) && selTurma.cursos.length > 0
                  ? selTurma.cursos
                  : courses.filter(cr => cr.id === selTurma.curso_id);
                if (turmaCursos.length <= 1) return null;
                return (
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Curso do Aluno nesta Turma Mista</label>
                    <select
                      name="curso_id"
                      required
                      value={enrollSelectedCursoId}
                      onChange={(e) => {
                        const cid = e.target.value;
                        setEnrollSelectedCursoId(cid);
                        const fullCourse = courses.find(cr => cr.id === parseInt(cid, 10));
                        if (fullCourse && fullCourse.valor_mensalidade != null) {
                          const valInput = document.getElementById('enroll_valor_mensalidade');
                          if (valInput) valInput.value = Number(fullCourse.valor_mensalidade).toFixed(2);
                        }
                      }}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="">-- Selecione o curso do aluno --</option>
                      {turmaCursos.map(cr => (
                        <option key={cr.id} value={cr.id}>{cr.nome}</option>
                      ))}
                    </select>
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Data da Matrícula</label>
                  <input
                    name="data_matricula"
                    type="date"
                    defaultValue={toLocalISODate()}
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Data de Início das Aulas</label>
                  <input
                    name="data_inicio"
                    type="date"
                    defaultValue={toLocalISODate()}
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Dia Preferencial de Vencimento</label>
                  <select
                    name="dia_vencimento"
                    defaultValue="10"
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="5">Dia 05 de cada mês</option>
                    <option value="10">Dia 10 de cada mês (Padrão)</option>
                    <option value="15">Dia 15 de cada mês</option>
                    <option value="20">Dia 20 de cada mês</option>
                    <option value="25">Dia 25 de cada mês</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Qtd. de Parcelas / Cobranças</label>
                  <select
                    name="quantidade_parcelas"
                    defaultValue="12"
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(n => (
                      <option key={n} value={n}>{n}x parcela{n > 1 ? 's' : ''} ({n} {n > 1 ? 'meses' : 'mês'})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="p-2.5 bg-blue-50 border border-blue-200/60 rounded-lg text-xs text-blue-800">
                💳 Ao confirmar a matrícula, o sistema gerará automaticamente todas as mensalidades do aluno no módulo Financeiro para acompanhamento e baixa de recebimento.
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input name="aula_experimental" type="checkbox" id="aula_exp" className="rounded text-amber-600" />
                <label htmlFor="aula_exp" className="text-xs text-slate-600 font-medium">
                  É uma aula experimental / cortesia <span className="text-slate-400">(não gera parcelas no Financeiro)</span>
                </label>
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
                <button
                  type="button"
                  onClick={() => {
                    setShowEnrollmentModal(false);
                    setModalError('');
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">
                  Confirmar Matrícula & Gerar Faturas
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EDITAR MATRÍCULA & CONTRATO */}
      {editingEnrollment && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Editar Matrícula #{editingEnrollment.id}</h3>
              <button
                onClick={() => {
                  setEditingEnrollment(null);
                  setModalError('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateEnrollment} className="space-y-4 mt-4">
              {modalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                  {modalError}
                </div>
              )}

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1 text-xs">
                <div><span className="font-semibold text-slate-700">Aluno:</span> {editingEnrollment.aluno_nome}</div>
                <div><span className="font-semibold text-slate-700">Turma:</span> {editingEnrollment.turma_nome}</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Status da Matrícula</label>
                  <select
                    name="status"
                    defaultValue={editingEnrollment.status}
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="ATIVA">ATIVA</option>
                    <option value="EXPERIMENTAL">EXPERIMENTAL</option>
                    <option value="TRANCADA">TRANCADA</option>
                    <option value="AGUARDANDO_RENOVACAO">AGUARDANDO RENOVAÇÃO</option>
                    <option value="CANCELADA">CANCELADA</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Valor Mensalidade (R$)</label>
                  <input
                    name="valor_mensalidade"
                    type="number"
                    step="0.01"
                    defaultValue={editingEnrollment.valor_mensalidade}
                    required
                    className="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800 outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Tipo de Desconto</label>
                  <select
                    name="tipo_desconto"
                    defaultValue={editingEnrollment.tipo_desconto || 'nenhum'}
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
                    defaultValue={editingEnrollment.desconto_percentual || 0}
                    min="0"
                    max="100"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Dia do Vencimento</label>
                  <select
                    name="dia_vencimento"
                    defaultValue={editingEnrollment.dia_vencimento || 10}
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="5">Dia 05</option>
                    <option value="10">Dia 10</option>
                    <option value="15">Dia 15</option>
                    <option value="20">Dia 20</option>
                    <option value="25">Dia 25</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Quantidade de Parcelas</label>
                  <select
                    name="quantidade_parcelas"
                    defaultValue={editingEnrollment.quantidade_parcelas || 12}
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(n => (
                      <option key={n} value={n}>{n}x</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  name="contrato_assinado"
                  type="checkbox"
                  id="edit_enr_contrato"
                  defaultChecked={editingEnrollment.contrato_assinado}
                  className="rounded text-amber-600"
                />
                <label htmlFor="edit_enr_contrato" className="text-xs text-slate-700 font-medium">
                  Contrato de Prestação de Serviços Assinado
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Motivo do Cancelamento (se aplicável)</label>
                <input
                  name="motivo_cancelamento"
                  defaultValue={editingEnrollment.motivo_cancelamento || ''}
                  placeholder="Ex: Mudança de cidade, incompatibilidade de horário..."
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Observações Internas</label>
                <textarea
                  name="observacoes"
                  rows="2"
                  defaultValue={editingEnrollment.observacoes || ''}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                ></textarea>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setEditingEnrollment(null);
                    setModalError('');
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: CRIAR / EDITAR TURMA */}
      {showClassModal && (() => {
        const selectedRoom = rooms.find(r => r.id === parseInt(classSalaId, 10));
        return (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="font-bold text-slate-800 text-base">
                  {editingClass ? 'Editar Turma' : 'Criar Nova Turma'}
                </h3>
                <button
                  onClick={() => {
                    setShowClassModal(false);
                    setEditingClass(null);
                  }}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form key={editingClass ? `edit-cls-${editingClass.id}` : 'new-cls'} onSubmit={handleSaveClass} className="space-y-4 mt-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Nome da Turma</label>
                  <input
                    name="nome"
                    required
                    defaultValue={editingClass?.nome || ''}
                    placeholder="Ex: Aquarela Avançada Quarta Tarde"
                    className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold text-slate-600">Cursos / Modalidades (Turma Mista)</label>
                    <span className="text-[11px] text-amber-700 font-semibold">{classSelectedCourses.length} selecionado(s)</span>
                  </div>
                  <div className="border rounded-lg p-2.5 max-h-36 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-1.5 bg-slate-50">
                    {courses.map(c => {
                      const checked = classSelectedCourses.includes(c.id);
                      return (
                        <label
                          key={c.id}
                          className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs cursor-pointer transition border ${
                            checked
                              ? 'bg-amber-50 border-amber-300 text-amber-900 font-semibold'
                              : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleClassCourse(c.id)}
                            className="rounded text-amber-600"
                          />
                          <span className="truncate">{c.nome}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Estúdio / Sala</label>
                    <select
                      name="sala_id"
                      required
                      value={classSalaId}
                      onChange={(e) => {
                        const sid = e.target.value;
                        setClassSalaId(sid);
                        const rObj = rooms.find(r => r.id === parseInt(sid, 10));
                        if (rObj) {
                          if (!editingClass || parseInt(classCapacidade || '0', 10) > rObj.capacidade) {
                            setClassCapacidade(String(rObj.capacidade));
                          }
                        }
                      }}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="">-- Selecione a sala --</option>
                      {rooms.map(r => (
                        <option key={r.id} value={r.id}>{r.nome} (Cap. {r.capacidade})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Capacidade da Turma</label>
                    <input
                      name="capacidade_maxima"
                      type="number"
                      min="1"
                      max={selectedRoom ? selectedRoom.capacidade : undefined}
                      required
                      value={classCapacidade}
                      onChange={(e) => setClassCapacidade(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                    />
                    {selectedRoom && (
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        Máximo da sala: {selectedRoom.capacidade} alunos
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold text-slate-600">Professor Responsável</label>
                    <button
                      type="button"
                      onClick={() => {
                        setShowClassModal(false);
                        setShowTeacherModal(true);
                      }}
                      className="text-xs text-amber-700 hover:underline font-semibold flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> Cadastrar Novo Professor
                    </button>
                  </div>
                  {teachers.length > 0 ? (
                    <select
                      name="professor_id"
                      required
                      defaultValue={editingClass?.professor_id || ''}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="">-- Selecione o professor --</option>
                      {teachers.map(t => <option key={t.id} value={t.id}>{t.nome} ({t.especialidades || 'Geral'})</option>)}
                    </select>
                  ) : (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center justify-between">
                      <span>Nenhum professor cadastrado ainda!</span>
                      <button
                        type="button"
                        onClick={() => {
                          setShowClassModal(false);
                          setShowTeacherModal(true);
                        }}
                        className="px-2 py-1 bg-red-600 text-white rounded font-semibold text-[11px]"
                      >
                        Cadastrar Agora
                      </button>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Faixa Etária *</label>
                    <select
                      name="faixa_etaria"
                      required
                      defaultValue={editingClass?.faixa_etaria || ''}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="">-- Selecione a faixa etária --</option>
                      <option value="INFANTIL">INFANTIL (7 a 10 anos)</option>
                      <option value="JUVENIL">JUVENIL (11 a 17 anos)</option>
                      <option value="ADULTO">ADULTO (18 a 65 anos)</option>
                      <option value="TERCEIRA_IDADE">TERCEIRA IDADE (65+)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Dia da Semana</label>
                    <select
                      name="dia_semana"
                      required
                      defaultValue={editingClass?.dia_semana || 'SEGUNDA'}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="SEGUNDA">Segunda-feira</option>
                      <option value="TERCA">Terça-feira</option>
                      <option value="QUARTA">Quarta-feira</option>
                      <option value="QUINTA">Quinta-feira</option>
                      <option value="SEXTA">Sexta-feira</option>
                      <option value="SABADO">Sábado</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Turno</label>
                    <select
                      name="turno"
                      required
                      defaultValue={editingClass?.turno || 'TARDE'}
                      className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                    >
                      <option value="MANHA">Manhã</option>
                      <option value="TARDE">Tarde</option>
                      <option value="NOITE">Noite</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Início (HH:MM)</label>
                    <input
                      name="horario_inicio"
                      type="text"
                      defaultValue={editingClass?.horario_inicio || '14:00'}
                      placeholder="14:00"
                      required
                      className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Término (HH:MM)</label>
                    <input
                      name="horario_fim"
                      type="text"
                      defaultValue={editingClass?.horario_fim || '16:00'}
                      placeholder="16:00"
                      required
                      className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                {editingClass && (
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      name="ativa"
                      type="checkbox"
                      id="class_active"
                      defaultChecked={editingClass.ativa}
                      className="rounded text-amber-600"
                    />
                    <label htmlFor="class_active" className="text-xs text-slate-700 font-medium">Turma Ativa</label>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setShowClassModal(false);
                      setEditingClass(null);
                    }}
                    className="px-4 py-2 text-xs font-semibold text-slate-600"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={teachers.length === 0}
                    className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow disabled:opacity-50"
                  >
                    {editingClass ? 'Salvar Alterações' : 'Salvar Turma'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        );
      })()}

      {/* MODAL: CRIAR / EDITAR SALA */}
      {showRoomModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">
                {editingRoom ? `Editar ${editingRoom.nome}` : 'Nova Sala / Estúdio'}
              </h3>
              <button
                onClick={() => {
                  setShowRoomModal(false);
                  setEditingRoom(null);
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form key={editingRoom ? `edit-room-${editingRoom.id}` : 'new-room'} onSubmit={handleSaveRoom} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome da Sala</label>
                <input
                  name="nome"
                  required
                  defaultValue={editingRoom?.nome || ''}
                  placeholder="Ex: Sala 1"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Capacidade Máxima (alunos)</label>
                <input
                  name="capacidade"
                  type="number"
                  min="1"
                  required
                  defaultValue={editingRoom?.capacidade ?? 9}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Descrição</label>
                <input
                  name="descricao"
                  defaultValue={editingRoom?.descricao || ''}
                  placeholder="Ex: Sala de desenho e pintura"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>
              {editingRoom && (
                <div className="flex items-center gap-2 pt-1">
                  <input
                    name="ativa"
                    type="checkbox"
                    id="room_active"
                    defaultChecked={editingRoom.ativa}
                    className="rounded text-amber-600"
                  />
                  <label htmlFor="room_active" className="text-xs text-slate-700 font-medium">Sala Ativa</label>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setShowRoomModal(false);
                    setEditingRoom(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow">
                  {editingRoom ? 'Salvar Alterações' : 'Cadastrar Sala'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: BAIXA DE PAGAMENTO */}
      {showPayModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">Baixa de Pagamento</h3>
              <button
                onClick={() => {
                  setShowPayModal(null);
                  setModalError('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-slate-500 mb-3">{showPayModal.descricao}</p>

            {modalError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium mb-3">
                {modalError}
              </div>
            )}

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
              <button
                onClick={() => {
                  setShowPayModal(null);
                  setModalError('');
                }}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600"
              >
                Cancelar
              </button>
              <button onClick={handlePayInvoice} className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow">
                Confirmar Recebimento
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CRIAR / EDITAR USUÁRIO (RBAC) */}
      {showUserModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base">
                {editingUser ? 'Editar Usuário' : 'Novo Usuário do Sistema'}
              </h3>
              <button
                onClick={() => {
                  setShowUserModal(false);
                  setEditingUser(null);
                  setModalError('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4 mt-4">
              {modalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-medium">
                  {modalError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nome Completo</label>
                <input
                  name="nome"
                  required
                  defaultValue={editingUser?.nome || ''}
                  placeholder="Ex: Maria Clara Santos"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">E-mail de Login</label>
                <input
                  name="email"
                  type="email"
                  required
                  defaultValue={editingUser?.email || ''}
                  placeholder="usuario@hbartes.com"
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Perfil de Acesso (RBAC)</label>
                <select
                  name="role"
                  value={userFormRole}
                  onChange={(e) => setUserFormRole(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                >
                  <option value="Direção">Direção / Administrador Geral (Acesso Completo)</option>
                  <option value="Coordenação">Coordenação Pedagógica (Turmas, Aulas e Alunos)</option>
                  <option value="Secretaria">Secretaria / Recepção (Atendimento, Alunos e Matrículas)</option>
                  <option value="Financeiro">Financeiro (Cobranças e Mensalidades)</option>
                  <option value="Professor">Professor (Acesso restrito às suas turmas)</option>
                </select>
              </div>

              {userFormRole === 'Professor' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Vincular ao Cadastro de Professor</label>
                  <select
                    name="professor_id"
                    defaultValue={editingUser?.professor_id || ''}
                    className="w-full px-3 py-2 border rounded-lg text-sm bg-white outline-none focus:border-amber-500"
                  >
                    <option value="">-- Selecione o professor --</option>
                    {teachers.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.nome} ({t.especialidades || 'Docente'})
                      </option>
                    ))}
                  </select>
                  <span className="text-[11px] text-slate-400 mt-1 block">
                    Permite ao professor visualizar somente as turmas que ele leciona ao fazer login.
                  </span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  {editingUser ? 'Alterar Senha (opcional)' : 'Senha de Acesso'}
                </label>
                <input
                  name="senha"
                  type="password"
                  required={!editingUser}
                  placeholder={editingUser ? 'Deixe vazio para manter a senha atual' : 'Mínimo 6 caracteres'}
                  className="w-full px-3 py-2 border rounded-lg text-sm outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  name="ativo"
                  type="checkbox"
                  id="user_active_chk"
                  defaultChecked={editingUser ? editingUser.ativo : true}
                  className="rounded text-amber-600"
                />
                <label htmlFor="user_active_chk" className="text-xs text-slate-700 font-medium">
                  Usuário Ativo (Pode realizar login)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setShowUserModal(false);
                    setEditingUser(null);
                    setModalError('');
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow"
                >
                  {editingUser ? 'Salvar Alterações' : 'Criar Usuário'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
