import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check: mengembalikan status koneksi dan orchestrator aktif
export const checkBackendHealth = async () => {
  try {
    const res = await apiClient.get('/health', { timeout: 4000 });
    return {
      online: res.status === 200,
      provider: res.data?.orchestrator_provider || null,
    };
  } catch {
    return { online: false, provider: null };
  }
};

// Kirim pesan async dengan batas toleransi inisiasi yang aman
export const sendChatMessageAsync = async (question, conversationId = '', provider = '') => {
  // 1. Inisiasi task (sertakan conversation_id & provider pilihan UI jika ada)
  const payload = { question };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }
  if (provider) {
    payload.provider = provider;
  }

  const initRes = await apiClient.post(
    '/chat/async',
    payload,
    { timeout: 30000 }
  );
  const { task_id } = initRes.data;

  // 2. Polling berkala hingga workflow Dify selesai menjawab
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const statusRes = await apiClient.get(`/chat/status/${task_id}`, {
          timeout: 15000,
        });
        const task = statusRes.data;

        if (task.status === 'completed') {
          clearInterval(interval);
          resolve({
            answer: task.answer,
            conversation_id: task.conversation_id,
            citations: task.citations || [],
          });
        } else if (task.status === 'failed') {
          clearInterval(interval);
          reject(new Error(task.detail || 'Terjadi kesalahan pada alur chat.'));
        }
        // Jika masih 'processing', interval terus berlanjut
      } catch (err) {
        clearInterval(interval);
        reject(err);
      }
    }, 1500); // Cek tiap 1.5 detik
  });
};
