'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardFooter, Button, Input, Select } from '@/components/ui';
import { FileUploader } from './FileUploader';
import { api } from '@/lib/api';
import { DEFAULT_MD_CONFIG, ENGINES, MACE_MODELS, DEVICES, ENSEMBLES, THERMOSTATS, type MDConfigType } from '@/lib/constants';
import { Activity, Settings, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

export function MDForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form state
  const [structureFile, setStructureFile] = useState<File[]>([]);
  const [config, setConfig] = useState<MDConfigType>(DEFAULT_MD_CONFIG);

  const updateConfig = <K extends keyof typeof config>(key: K, value: typeof config[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (structureFile.length === 0) {
      toast.error('구조 파일을 업로드해주세요.');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('structure', structureFile[0]);
      formData.append('config', JSON.stringify(config));

      const result = await api.createMDJob(formData);
      toast.success('MD 시뮬레이션 작업이 생성되었습니다.');
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
  const ensembleOptions = ENSEMBLES.map(e => ({ value: e, label: e.toUpperCase() }));
  const thermostatOptions = THERMOSTATS.map(t => ({ value: t, label: t.replace('_', ' ') }));

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-6">
        {/* 파일 업로드 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              Structure File
            </h3>
          </CardHeader>
          <CardContent>
            <FileUploader
              label="Structure (with adsorbed molecule)"
              value={structureFile}
              onChange={setStructureFile}
              multiple={false}
            />
          </CardContent>
        </Card>

        {/* MD 설정 */}
        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <Settings className="w-5 h-5" />
              MD Configuration
            </h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Select
                label="Ensemble"
                options={ensembleOptions}
                value={config.ensemble}
                onChange={(e) => updateConfig('ensemble', e.target.value as typeof config.ensemble)}
              />
              <Input
                label="Temperature (K)"
                type="number"
                value={config.temperature}
                onChange={(e) => updateConfig('temperature', parseFloat(e.target.value))}
                min={0}
              />
              {config.ensemble === 'npt' && (
                <Input
                  label="Pressure (bar)"
                  type="number"
                  step="0.1"
                  value={config.pressure}
                  onChange={(e) => updateConfig('pressure', parseFloat(e.target.value))}
                />
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              <Select
                label="Thermostat"
                options={thermostatOptions}
                value={config.thermostat}
                onChange={(e) => updateConfig('thermostat', e.target.value as typeof config.thermostat)}
              />
              <Input
                label="Timestep (fs)"
                type="number"
                step="0.1"
                value={config.timestep}
                onChange={(e) => updateConfig('timestep', parseFloat(e.target.value))}
              />
              <Input
                label="Total Steps"
                type="number"
                value={config.steps}
                onChange={(e) => updateConfig('steps', parseInt(e.target.value))}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
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
                  label="Log Interval (steps)"
                  type="number"
                  value={config.log_interval}
                  onChange={(e) => updateConfig('log_interval', parseInt(e.target.value))}
                />
                <Input
                  label="Trajectory Interval (steps)"
                  type="number"
                  value={config.traj_interval}
                  onChange={(e) => updateConfig('traj_interval', parseInt(e.target.value))}
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
                Start MD Simulation
              </Button>
            </div>
          </CardFooter>
        </Card>
      </div>
    </form>
  );
}
