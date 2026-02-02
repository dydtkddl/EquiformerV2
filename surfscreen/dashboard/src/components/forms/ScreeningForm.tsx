'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardFooter, Button, Input, Select } from '@/components/ui';
import { FileUploader } from './FileUploader';
import { api } from '@/lib/api';
import { DEFAULT_SCREENING_CONFIG, ENGINES, MACE_MODELS, DEVICES } from '@/lib/constants';
import { Zap, Settings, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

export function ScreeningForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form state
  const [surfaceFile, setSurfaceFile] = useState<File[]>([]);
  const [moleculeFiles, setMoleculeFiles] = useState<File[]>([]);
  const [config, setConfig] = useState(DEFAULT_SCREENING_CONFIG);

  const updateConfig = <K extends keyof typeof config>(key: K, value: typeof config[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (surfaceFile.length === 0) {
      toast.error('표면 파일을 업로드해주세요.');
      return;
    }
    if (moleculeFiles.length === 0) {
      toast.error('분자 파일을 업로드해주세요.');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('surface', surfaceFile[0]);
      moleculeFiles.forEach(file => formData.append('molecules', file));
      formData.append('config', JSON.stringify(config));

      const result = await api.createScreeningJob(formData);
      toast.success('스크리닝 작업이 생성되었습니다.');
      router.push(`/jobs/${result.job_id}`);
    } catch (error) {
      toast.error('작업 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const engineOptions = ENGINES.map(e => ({ value: e, label: e.toUpperCase() }));
  const modelOptions = MACE_MODELS.map(m => ({ value: m, label: m }));
  const deviceOptions = DEVICES.map(d => ({ value: d, label: d.toUpperCase() }));

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-6">
        {/* 파일 업로드 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Files
            </h3>
          </CardHeader>
          <CardContent className="space-y-6">
            <FileUploader
              label="Surface Structure"
              value={surfaceFile}
              onChange={setSurfaceFile}
              multiple={false}
            />
            <FileUploader
              label="Molecules"
              value={moleculeFiles}
              onChange={setMoleculeFiles}
              multiple={true}
            />
          </CardContent>
        </Card>

        {/* 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Configuration
            </h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Select
                label="Engine"
                options={engineOptions}
                value={config.engine}
                onChange={(e) => updateConfig('engine', e.target.value)}
              />
              {config.engine === 'mace' && (
                <Select
                  label="Model"
                  options={modelOptions}
                  value={config.model}
                  onChange={(e) => updateConfig('model', e.target.value)}
                />
              )}
              <Select
                label="Device"
                options={deviceOptions}
                value={config.device}
                onChange={(e) => updateConfig('device', e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <Input
                label="Max Configurations"
                type="number"
                value={config.max_configs}
                onChange={(e) => updateConfig('max_configs', parseInt(e.target.value))}
                min={1}
                max={200}
              />
              <Input
                label="Fix Layers"
                type="number"
                value={config.fix_layers}
                onChange={(e) => updateConfig('fix_layers', parseInt(e.target.value))}
                min={0}
                max={5}
              />
            </div>

            {/* Advanced */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 mt-4 text-sm text-gray-500 hover:text-gray-700"
            >
              {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              Advanced Options
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Input
                  label="Force Convergence (fmax)"
                  type="number"
                  step="0.01"
                  value={config.fmax}
                  onChange={(e) => updateConfig('fmax', parseFloat(e.target.value))}
                />
                <Input
                  label="Max Optimization Steps"
                  type="number"
                  value={config.steps}
                  onChange={(e) => updateConfig('steps', parseInt(e.target.value))}
                />
              </div>
            )}
          </CardContent>
          <CardFooter>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Cancel
              </Button>
              <Button type="submit" loading={loading}>
                Start Screening
              </Button>
            </div>
          </CardFooter>
        </Card>
      </div>
    </form>
  );
}
