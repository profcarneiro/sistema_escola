const API_BASE = '/api/v1';

export const authStorage = {
  getToken: () => localStorage.getItem('hb_token'),
  getUser: () => {
    const u = localStorage.getItem('hb_user');
    return u ? JSON.parse(u) : null;
  },
  setAuth: (token, user) => {
    localStorage.setItem('hb_token', token);
    localStorage.setItem('hb_user', JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem('hb_token');
    localStorage.removeItem('hb_user');
  }
};

export async function request(endpoint, options = {}) {
  const token = authStorage.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    authStorage.clear();
    window.location.reload();
    throw new Error('Sessão expirada. Por favor faça login novamente.');
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    const data = await response.json();
    if (!response.ok) {
      let errorMsg = 'Ocorreu um erro na requisição.';
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail
          .map(d => {
            if (typeof d === 'string') return d;
            const field = d.loc ? d.loc[d.loc.length - 1] : '';
            return field && field !== 'body' ? `${field}: ${d.msg}` : (d.msg || JSON.stringify(d));
          })
          .join('; ');
      } else if (data.detail && typeof data.detail === 'object') {
        errorMsg = data.detail.msg || data.detail.message || JSON.stringify(data.detail);
      } else if (data.message) {
        errorMsg = data.message;
      }
      throw new Error(errorMsg);
    }
    return data;
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Ocorreu um erro na requisição.');
  }

  return response.text();
}

async function downloadBlob(endpoint, fallbackFilename) {
  const token = authStorage.getToken();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  });

  if (response.status === 401) {
    authStorage.clear();
    window.location.reload();
    throw new Error('Sessão expirada. Por favor faça login novamente.');
  }

  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      throw new Error(data.detail || 'Erro ao baixar arquivo.');
    }
    throw new Error('Erro ao baixar arquivo.');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fallbackFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export const api = {
  // Autenticação
  login: (email, senha) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, senha })
  }),
  getMe: () => request('/auth/me'),

  // Dashboard & Relatórios
  getDashboard: (competencia = '') => request(`/reports/dashboard${competencia ? `?competencia=${competencia}` : ''}`),
  getRoomOccupancy: () => request('/reports/room-occupancy'),
  exportStudentsUrl: `${API_BASE}/reports/export/students-csv`,
  exportInvoicesUrl: `${API_BASE}/reports/export/invoices-csv`,

  // Salas & Cursos
  getRooms: () => request('/rooms/'),
  createRoom: (data) => request('/rooms/', { method: 'POST', body: JSON.stringify(data) }),
  updateRoom: (id, data) => request(`/rooms/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRoom: (id) => request(`/rooms/${id}`, { method: 'DELETE' }),
  getCourses: () => request('/courses/'),
  createCourse: (data) => request('/courses/', { method: 'POST', body: JSON.stringify(data) }),
  updateCourse: (id, data) => request(`/courses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCourse: (id) => request(`/courses/${id}`, { method: 'DELETE' }),

  // Professores
  getTeachers: () => request('/teachers/'),
  createTeacher: (data) => request('/teachers/', { method: 'POST', body: JSON.stringify(data) }),
  updateTeacher: (id, data) => request(`/teachers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTeacher: (id) => request(`/teachers/${id}`, { method: 'DELETE' }),

  // Turmas
  getClasses: () => request('/classes/'),
  createClass: (data) => request('/classes/', { method: 'POST', body: JSON.stringify(data) }),
  updateClass: (id, data) => request(`/classes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteClass: (id) => request(`/classes/${id}`, { method: 'DELETE' }),

  // Alunos & Responsáveis
  getStudents: (params = '') => request(`/students/?${params}`),
  getStudent: (id) => request(`/students/${id}`),
  createStudent: (data) => request('/students/', { method: 'POST', body: JSON.stringify(data) }),
  updateStudent: (id, data) => request(`/students/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteStudent: (id) => request(`/students/${id}`, { method: 'DELETE' }),
  updateGuardian: (alunoId, data) => request(`/students/${alunoId}/responsavel`, { method: 'PUT', body: JSON.stringify(data) }),

  // Matrículas & Espera
  getEnrollments: () => request('/enrollments/'),
  createEnrollment: (data) => request('/enrollments/', { method: 'POST', body: JSON.stringify(data) }),
  updateEnrollment: (id, data) => request(`/enrollments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteEnrollment: (id) => request(`/enrollments/${id}`, { method: 'DELETE' }),
  generateEnrollmentInvoices: (matriculaId) => request(`/enrollments/${matriculaId}/generate-invoices`, { method: 'POST' }),
  getWaitlist: (turmaId) => request(`/enrollments/waitlist/${turmaId}`),

  // Frequência & Diário
  getLessons: (turmaId) => request(`/attendance/lessons?turma_id=${turmaId || ''}`),
  createLesson: (data) => request('/attendance/lessons', { method: 'POST', body: JSON.stringify(data) }),
  recordAttendance: (lessonId, frequencias, motivoAlteracao = null) => request(`/attendance/lessons/${lessonId}/batch`, {
    method: 'POST',
    body: JSON.stringify({ frequencias, motivo_alteracao: motivoAlteracao })
  }),
  updateLesson: (lessonId, data) => request(`/attendance/lessons/${lessonId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }),
  getMakeups: () => request('/attendance/makeups'),
  createMakeup: (data) => request('/attendance/makeups', { method: 'POST', body: JSON.stringify(data) }),
  getAttendanceClassesSummary: () => request('/attendance/reports/classes-summary'),
  getAttendanceStudentHistory: (alunoId) => request(`/attendance/reports/student-history?aluno_id=${alunoId}`),
  getMissingCallAlerts: (competencia = '') =>
    request(`/attendance/alerts/missing-calls${competencia ? `?competencia=${competencia}` : ''}`),
  getMonthlyStudentsAttendance: (competencia, turmaId = '') =>
    request(`/attendance/reports/monthly-students?competencia=${competencia}${turmaId ? `&turma_id=${turmaId}` : ''}`),

  // Gestão de Usuários e Acessos
  getUsers: () => request('/users/'),
  createUser: (data) => request('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),

  // Financeiro & DRE
  getInvoices: () => request('/financial/invoices'),
  payInvoice: (id, data) => request(`/financial/invoices/${id}/pay`, { method: 'POST', body: JSON.stringify(data) }),
  generateMonthly: (competencia) => request(`/financial/invoices/generate-monthly?competencia=${competencia}`, { method: 'POST' }),
  syncEnrollmentInvoices: () => request('/financial/invoices/sync-enrollments', { method: 'POST' }),
  getDefaulters: () => request('/financial/defaulters'),
  getCashFlow: (inicio, fim) => request(`/financial/cash-flow?data_inicio=${inicio}&data_fim=${fim}`),
  getDRE: (inicio, fim, alunoId = null) => request(`/financial/dre?competencia_inicio=${inicio}&competencia_fim=${fim}${alunoId ? `&aluno_id=${alunoId}` : ''}`),
  getDiscountsReport: (params = '') => request(`/financial/discounts-report${params ? `?${params}` : ''}`),

  // Despesas & Centros de Custo
  getExpenses: (params = '') => request(`/financial/expenses${params ? `?${params}` : ''}`),
  createExpense: (data) => request('/financial/expenses', { method: 'POST', body: JSON.stringify(data) }),
  updateExpense: (id, data) => request(`/financial/expenses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteExpense: (id) => request(`/financial/expenses/${id}`, { method: 'DELETE' }),
  exportExpensesCsv: (params = '') =>
    downloadBlob(`/financial/expenses/export-csv${params ? `?${params}` : ''}`, 'despesas_escola_hb.csv'),
  getCostCenters: () => request('/financial/cost-centers'),
  createCostCenter: (data) => request('/financial/cost-centers', { method: 'POST', body: JSON.stringify(data) }),
  getCostCentersReport: (params = '') => request(`/financial/cost-centers/report${params ? `?${params}` : ''}`),
  getMonthlyCashFlow: (ano) => request(`/financial/cash-flow-monthly${ano ? `?ano=${ano}` : ''}`),
  getForecastSettings: () => request('/financial/forecast/settings'),
  updateForecastSettings: (data) => request('/financial/forecast/settings', { method: 'PUT', body: JSON.stringify(data) }),
  getForecast12Months: (params = '') => request(`/financial/forecast-12m${params ? `?${params}` : ''}`),
  getStudentMonthlyMatrix: (params = '') => request(`/financial/student-monthly-matrix${params ? `?${params}` : ''}`),

  // Operacional: Pagamento de Professores, Comercial & Ateliê Parceria
  getTeacherRules: (professorId = '') =>
    request(`/operations/teachers/rules${professorId ? `?professor_id=${professorId}` : ''}`),
  upsertTeacherRule: (data) => request('/operations/teachers/rules', { method: 'PUT', body: JSON.stringify(data) }),
  deleteTeacherRule: (id) => request(`/operations/teachers/rules/${id}`, { method: 'DELETE' }),
  generateTeacherClosings: (data) =>
    request('/operations/teachers/closings/generate', { method: 'POST', body: JSON.stringify(data) }),
  getTeacherClosings: (competencia = '', professorId = '') => {
    const qs = new URLSearchParams();
    if (competencia) qs.set('competencia', competencia);
    if (professorId) qs.set('professor_id', professorId);
    const s = qs.toString();
    return request(`/operations/teachers/closings${s ? `?${s}` : ''}`);
  },
  payTeacherClosing: (id, data) =>
    request(`/operations/teachers/closings/${id}/pay`, { method: 'POST', body: JSON.stringify(data) }),
  reopenTeacherClosing: (id) =>
    request(`/operations/teachers/closings/${id}/reopen`, { method: 'POST' }),
  getAttendanceChangeLogs: (competencia = '') =>
    request(`/operations/teachers/change-logs${competencia ? `?competencia=${competencia}` : ''}`),

  getCommercialConfig: () => request('/operations/commercial/config'),
  updateCommercialConfig: (data) => request('/operations/commercial/config', { method: 'PUT', body: JSON.stringify(data) }),
  generateCommercialClosing: (competencia) =>
    request(`/operations/commercial/closings/generate?competencia=${competencia}`, { method: 'POST' }),
  getCommercialClosings: () => request('/operations/commercial/closings'),
  payCommercialClosing: (id, data) =>
    request(`/operations/commercial/closings/${id}/pay`, { method: 'POST', body: JSON.stringify(data) }),

  getWorkshops: (competencia = '') =>
    request(`/operations/workshops${competencia ? `?competencia=${competencia}` : ''}`),
  createWorkshop: (data) => request('/operations/workshops', { method: 'POST', body: JSON.stringify(data) }),
  deleteWorkshop: (id) => request(`/operations/workshops/${id}`, { method: 'DELETE' }),
  addWorkshopParticipant: (workshopId, data) =>
    request(`/operations/workshops/${workshopId}/participants`, { method: 'POST', body: JSON.stringify(data) }),
  deleteWorkshopParticipant: (participantId) =>
    request(`/operations/workshops/participants/${participantId}`, { method: 'DELETE' }),
  payWorkshopTransfer: (workshopId, data) =>
    request(`/operations/workshops/${workshopId}/pay-transfer`, { method: 'POST', body: JSON.stringify(data) }),
  getWorkshopsSummary: (competencia) =>
    request(`/operations/workshops/summary?competencia=${competencia}`),

  // Planos e Descontos
  getDiscountPolicies: () => request('/discount-policies/'),
  updateDiscountSettings: (data) => request('/discount-policies/settings', { method: 'PUT', body: JSON.stringify(data) }),
  createPaymentPlan: (data) => request('/discount-policies/plans', { method: 'POST', body: JSON.stringify(data) }),
  updatePaymentPlan: (id, data) => request(`/discount-policies/plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePaymentPlan: (id) => request(`/discount-policies/plans/${id}`, { method: 'DELETE' }),
  upsertCourseDiscountRule: (data) => request('/discount-policies/course-rules', { method: 'PUT', body: JSON.stringify(data) }),
  simulateDiscountPolicy: (data) => request('/discount-policies/simulate', { method: 'POST', body: JSON.stringify(data) }),

  // WhatsApp
  getInvoiceReminderLink: (invoiceId) => request(`/communication/whatsapp-invoice-reminder/${invoiceId}`, { method: 'POST' }),
  getEnrollmentWelcomeLink: (matriculaId) => request(`/communication/whatsapp-enrollment-welcome/${matriculaId}`, { method: 'POST' }),
  getCustomWhatsAppLink: (data) => request('/communication/whatsapp-custom-link', { method: 'POST', body: JSON.stringify(data) }),

  // Backups Locais & Remotos (Supabase)
  getBackups: () => request('/backup/list'),
  createBackup: (enviarRemoto = null) =>
    request(`/backup/create${enviarRemoto !== null ? `?enviar_remoto=${enviarRemoto}` : ''}`, { method: 'POST' }),
  downloadLocalBackup: (filename) => downloadBlob(`/backup/download/${encodeURIComponent(filename)}`, filename),
  getRemoteBackupStatus: () => request('/backup/remote/status'),
  saveRemoteBackupConfig: (data) => request('/backup/remote/config', { method: 'PUT', body: JSON.stringify(data) }),
  testRemoteBackup: () => request('/backup/remote/test', { method: 'POST' }),
  syncRemoteBackupNow: () => request('/backup/remote/sync-now', { method: 'POST' }),
  uploadBackupToRemote: (filename) => request(`/backup/remote/upload/${encodeURIComponent(filename)}`, { method: 'POST' }),
  getRemoteBackups: () => request('/backup/remote/list'),
  downloadRemoteBackup: (filename) => downloadBlob(`/backup/remote/download/${encodeURIComponent(filename)}`, filename),
  pullRemoteBackup: (filename) => request(`/backup/remote/pull/${encodeURIComponent(filename)}`, { method: 'POST' }),
  deleteRemoteBackup: (filename) => request(`/backup/remote/${encodeURIComponent(filename)}`, { method: 'DELETE' }),
};
