import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Setup = () => {
  const navigate = useNavigate();
  const [demoMode, setDemoMode] = useState(true);
  const [supabaseUrl, setSupabaseUrl] = useState(
    localStorage.getItem('supabaseUrl') || ''
  );
  const [supabaseKey, setSupabaseKey] = useState(
    localStorage.getItem('supabaseKey') || ''
  );
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem('apiUrl') || 'http://localhost:8000'
  );

  const handleSave = (e) => {
    e.preventDefault();

    if (demoMode) {
      localStorage.removeItem('supabaseUrl');
      localStorage.removeItem('supabaseKey');
    } else {
      if (!supabaseUrl || !supabaseKey) {
        alert('Пожалуйста, введите URL и ключ Supabase');
        return;
      }
      localStorage.setItem('supabaseUrl', supabaseUrl);
      localStorage.setItem('supabaseKey', supabaseKey);
    }

    localStorage.setItem('apiUrl', apiUrl);
    localStorage.setItem('demoMode', String(demoMode));

    navigate('/');
  };

  const handleReset = () => {
    localStorage.clear();
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-blue-900 mb-2">
              ⚙️ Настройка системы
            </h1>
            <p className="text-gray-700">
              Выберите режим работы и укажите параметры подключения
            </p>
          </div>

          <form onSubmit={handleSave} className="space-y-6">
            {/* Mode Selection */}
            <div className="border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">📋 Режим работы</h2>

              <div className="space-y-3">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    checked={demoMode}
                    onChange={() => setDemoMode(true)}
                    className="w-4 h-4 mr-3"
                  />
                  <div>
                    <p className="font-semibold text-green-700">
                      ✅ Демо режим (рекомендуется)
                    </p>
                    <p className="text-sm text-gray-600">
                      Использует встроенные примеры данных, не требует конфигурации
                    </p>
                  </div>
                </label>

                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    checked={!demoMode}
                    onChange={() => setDemoMode(false)}
                    className="w-4 h-4 mr-3"
                  />
                  <div>
                    <p className="font-semibold text-blue-700">
                      🔗 Режим Supabase
                    </p>
                    <p className="text-sm text-gray-600">
                      Подключение к внешней базе данных Supabase
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Supabase Config (if not demo mode) */}
            {!demoMode && (
              <div className="border border-yellow-300 bg-yellow-50 rounded-lg p-4 space-y-4">
                <h2 className="text-lg font-semibold text-yellow-900">
                  🔑 Учетные данные Supabase
                </h2>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-gray-700">
                    Supabase URL
                  </label>
                  <input
                    type="text"
                    value={supabaseUrl}
                    onChange={(e) => setSupabaseUrl(e.target.value)}
                    placeholder="https://xxxxx.supabase.co"
                    className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    Найти в Settings → API в Supabase dashboard
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-gray-700">
                    Supabase Anon Key
                  </label>
                  <input
                    type="password"
                    value={supabaseKey}
                    onChange={(e) => setSupabaseKey(e.target.value)}
                    placeholder="eyJhbGc..."
                    className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    Найти в Settings → API → Anon key
                  </p>
                </div>
              </div>
            )}

            {/* API URL */}
            <div className="border rounded-lg p-4">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                🔗 Backend API URL
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-600 mt-1">
                Адрес вашего FastAPI сервера (по умолчанию: http://localhost:8000)
              </p>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                type="submit"
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded transition-colors"
              >
                ✓ Сохранить и продолжить
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="px-6 bg-red-100 hover:bg-red-200 text-red-700 font-bold py-3 rounded transition-colors"
              >
                🔄 Сброс
              </button>
            </div>
          </form>

          {/* Info */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-gray-700 space-y-2">
            <p>
              <strong>💡 Совет:</strong> Для быстрого начала используйте демо режим
              с встроенными примерами данных.
            </p>
            <p>
              <strong>🔐 Безопасность:</strong> Ключи Supabase хранятся в
              localStorage браузера. Не используйте ключи service role!
            </p>
            <p>
              <strong>📚 Документация:</strong> Подробнее о Supabase найти на{' '}
              <a
                href="https://supabase.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                supabase.com
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Setup;
