import { useState } from "react";
import { TextField, Button, Card, CardContent, Typography, Alert } from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Login() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    setError("");
    
    const formData = new FormData();
    formData.append("username", form.username);
    formData.append("password", form.password);

    api.post("/auth/token", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    })
      .then((response) => {
        localStorage.setItem("token", response.data.access_token);
        navigate("/recetas");
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Error al iniciar sesión");
      });
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card sx={{ maxWidth: 400, width: '100%', p: 2 }}>
        <CardContent>
          <Typography variant="h4" align="center" gutterBottom>
            Sistema de Recetas
          </Typography>
          <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 3 }}>
            Iniciar Sesión
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleLogin}>
            <TextField
              label="Usuario"
              fullWidth
              margin="normal"
              required
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
            <TextField
              label="Contraseña"
              type="password"
              fullWidth
              margin="normal"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <Button
              type="submit"
              variant="contained"
              fullWidth
              sx={{ mt: 3, mb: 2 }}
            >
              Iniciar Sesión
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}



