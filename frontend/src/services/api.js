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
      throw new Error(data.detail || 'Ocorreu um erro na requisição.');
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
  getTeachers: () => request('/teachers/'),
  getClasses: () => request('/classes/'),
  createClass: (data) => request('/classes/', { method: 'POST', body: JSON.stringify(data) }),

  // Alunos & Responsáveis
  getStudents: (params = '') => request(`/students/?${params}`),
  getStudent: (id) => request(`/students/${id}`),
  createStudent: (data) => request('/students/', { method: 'POST', body: JSON.stringify(data) }),

  // Matrículas & Espera
  getEnrollments: () => request('/enrollments/'),
  createEnrollment: (data) => request('/enrollments/', { method: 'POST', body: JSON.stringify(data) }),
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

  // Financeiro & DRE
  getInvoices: () => request('/financial/invoices'),
  payInvoice: (id, data) => request(`/financial/invoices/${id}/pay`, { method: 'POST', body: JSON.stringify(data) }),
  generateMonthly: (competencia) => request(`/financial/invoices/generate-monthly?competencia=${competencia}`, { method: 'POST' }),
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
