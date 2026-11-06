import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check: 4 detik cukup
export const checkBackendHealth = async () => {
  try {
    const res = await apiClient.get('/health', { timeout: 4000 });
    return res.status === 200;
  } catch {
    return false;
  }
};

// Kirim pesan async dengan batas toleransi inisiasi yang aman
export const sendChatMessageAsync = async (question) => {
  // 1. Inisiasi task (beri waktu 30 detik untuk mengantisipasi inisiasi koneksi/subproses)
  const initRes = await apiClient.post(
    '/chat/async',
    { question },
    { timeout: 30000 }
  );
  const { task_id } = initRes.data;

  // 2. Polling berkala hingga LLM selesai menjawab
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
            citations: task.citations || [],
          });
        } else if (task.status === 'failed') {
          clearInterval(interval);
          reject(new Error(task.detail || 'Terjadi kesalahan pada alur RAG.'));
        }
        // Jika masih 'processing', interval terus berlanjut
      } catch (err) {
        clearInterval(interval);
        reject(err);
      }
    }, 1500); // Cek tiap 1.5 detik
  });
};