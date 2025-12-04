import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000/api";

console.log("[API] Base URL:", API_BASE);

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para añadir token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor de errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("[API Error]", error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export default api;
