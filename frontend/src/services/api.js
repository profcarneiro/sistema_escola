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

export const api = {
  // Autenticação
  login: (email, senha) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, senha })
  }),
  getMe: () => request('/auth/me'),

  // Dashboard & Relatórios
  getDashboard: () => request('/reports/dashboard'),
  getRoomOccupancy: () => request('/reports/room-occupancy'),
  exportStudentsUrl: `${API_BASE}/reports/export/students-csv`,
  exportInvoicesUrl: `${API_BASE}/reports/export/invoices-csv`,

  // Salas & Cursos
  getRooms: () => request('/rooms/'),
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

  // Alunos & Responsáveis
  getStudents: (params = '') => request(`/students/?${params}`),
  getStudent: (id) => request(`/students/${id}`),
  createStudent: (data) => request('/students/', { method: 'POST', body: JSON.stringify(data) }),
  updateStudent: (id, data) => request(`/students/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateGuardian: (alunoId, data) => request(`/students/${alunoId}/responsavel`, { method: 'PUT', body: JSON.stringify(data) }),

  // Matrículas & Espera
  getEnrollments: () => request('/enrollments/'),
  createEnrollment: (data) => request('/enrollments/', { method: 'POST', body: JSON.stringify(data) }),
  updateEnrollment: (id, data) => request(`/enrollments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  generateEnrollmentInvoices: (matriculaId) => request(`/enrollments/${matriculaId}/generate-invoices`, { method: 'POST' }),
  getWaitlist: (turmaId) => request(`/enrollments/waitlist/${turmaId}`),

  // Frequência & Diário
  getLessons: (turmaId) => request(`/attendance/lessons?turma_id=${turmaId || ''}`),
  createLesson: (data) => request('/attendance/lessons', { method: 'POST', body: JSON.stringify(data) }),
  recordAttendance: (lessonId, frequencias) => request(`/attendance/lessons/${lessonId}/batch`, {
    method: 'POST',
    body: JSON.stringify({ frequencias })
  }),
  getMakeups: () => request('/attendance/makeups'),
  createMakeup: (data) => request('/attendance/makeups', { method: 'POST', body: JSON.stringify(data) }),
  getAttendanceClassesSummary: () => request('/attendance/reports/classes-summary'),
  getAttendanceStudentHistory: (alunoId) => request(`/attendance/reports/student-history?aluno_id=${alunoId}`),

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
  getDRE: (inicio, fim) => request(`/financial/dre?competencia_inicio=${inicio}&competencia_fim=${fim}`),

  // WhatsApp
  getInvoiceReminderLink: (invoiceId) => request(`/communication/whatsapp-invoice-reminder/${invoiceId}`, { method: 'POST' }),
  getEnrollmentWelcomeLink: (matriculaId) => request(`/communication/whatsapp-enrollment-welcome/${matriculaId}`, { method: 'POST' }),
  getCustomWhatsAppLink: (data) => request('/communication/whatsapp-custom-link', { method: 'POST', body: JSON.stringify(data) }),

  // Backups
  getBackups: () => request('/backup/list'),
  createBackup: () => request('/backup/create', { method: 'POST' }),
};
