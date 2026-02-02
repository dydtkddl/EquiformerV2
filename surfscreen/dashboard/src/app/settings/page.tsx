'use client';

import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardFooter, Button, Input, Select } from '@/components/ui';
import { useSettingsStore } from '@/stores';
import { useTheme } from '@/hooks';
import { Settings as SettingsIcon, Save, RotateCcw, Moon, Sun, Monitor } from 'lucide-react';
import { ENGINES, DEVICES } from '@/lib/constants';
import toast from 'react-hot-toast';
import { useState } from 'react';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const settings = useSettingsStore();
  
  const [apiUrl, setApiUrl] = useState(settings.apiUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey);
  const [showApiKey, setShowApiKey] = useState(false);

  const handleSave = () => {
    settings.setApiUrl(apiUrl);
    settings.setApiKey(apiKey);
    toast.success('설정이 저장되었습니다.');
  };

  const handleReset = () => {
    if (!confirm('모든 설정을 초기화하시겠습니까?')) return;
    settings.reset();
    setApiUrl(settings.apiUrl);
    setApiKey(settings.apiKey);
    toast.success('설정이 초기화되었습니다.');
  };

  const themeOptions = [
    { value: 'dark', label: 'Dark' },
    { value: 'light', label: 'Light' },
    { value: 'system', label: 'System' }
  ];

  const engineOptions = ENGINES.map(e => ({ value: e, label: e.toUpperCase() }));
  const deviceOptions = DEVICES.map(d => ({ value: d, label: d.toUpperCase() }));

  return (
    <MainLayout title="Settings">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <SettingsIcon className="w-6 h-6" />
            Settings
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            대시보드 설정을 관리합니다.
          </p>
        </div>

        {/* API 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">API Configuration</h3>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="API URL"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <div className="relative">
              <Input
                label="API Key"
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter API key"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-8 text-sm text-blue-500"
              >
                {showApiKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* 테마 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Appearance</h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {themeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value as 'dark' | 'light' | 'system')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === option.value
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  {option.value === 'dark' && <Moon className="w-6 h-6" />}
                  {option.value === 'light' && <Sun className="w-6 h-6" />}
                  {option.value === 'system' && <Monitor className="w-6 h-6" />}
                  <span className="text-sm font-medium">{option.label}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 기본값 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Defaults</h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Default Engine"
                options={engineOptions}
                value={settings.defaultEngine}
                onChange={(e) => settings.setDefaultEngine(e.target.value)}
              />
              <Select
                label="Default Device"
                options={deviceOptions}
                value={settings.defaultDevice}
                onChange={(e) => settings.setDefaultDevice(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Polling 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold">Real-time Updates</h3>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900 dark:text-white">Auto Refresh</p>
                <p className="text-sm text-gray-500">자동으로 데이터를 새로고침합니다.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={settings.pollingEnabled}
                  onChange={(e) => settings.setPollingEnabled(e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </CardContent>
        </Card>

        {/* 액션 버튼 */}
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={handleReset}
            icon={<RotateCcw className="w-4 h-4" />}
          >
            Reset
          </Button>
          <Button
            onClick={handleSave}
            icon={<Save className="w-4 h-4" />}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </MainLayout>
  );
}
