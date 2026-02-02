'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { cn, formatFileSize } from '@/lib/utils';
import { ALLOWED_EXTENSIONS } from '@/lib/constants';
import { Upload, X, File } from 'lucide-react';
import { Button } from '@/components/ui';

interface FileUploaderProps {
  label?: string;
  accept?: string[];
  multiple?: boolean;
  maxSize?: number;
  value: File[];
  onChange: (files: File[]) => void;
  error?: string;
}

export function FileUploader({
  label,
  accept = ALLOWED_EXTENSIONS,
  multiple = false,
  maxSize = 50 * 1024 * 1024, // 50MB
  value,
  onChange,
  error
}: FileUploaderProps) {
  const [preview, setPreview] = useState<string>('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (multiple) {
      onChange([...value, ...acceptedFiles]);
    } else {
      onChange(acceptedFiles.slice(0, 1));
      // 첫 10줄 미리보기
      if (acceptedFiles[0]) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          const lines = content.split('\n').slice(0, 10).join('\n');
          setPreview(lines);
        };
        reader.readAsText(acceptedFiles[0].slice(0, 5000));
      }
    }
  }, [value, onChange, multiple]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: accept.reduce((acc, ext) => {
      acc[`application/${ext.replace('.', '')}`] = [ext];
      return acc;
    }, {} as Record<string, string[]>),
    maxSize,
    multiple
  });

  const removeFile = (index: number) => {
    const newFiles = [...value];
    newFiles.splice(index, 1);
    onChange(newFiles);
    if (!multiple) setPreview('');
  };

  return (
    <div className="w-full">
      {label && (
        <label className="block mb-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400',
          error && 'border-red-500'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {isDragActive ? (
            '파일을 놓아주세요'
          ) : (
            <>
              <span className="text-blue-500">클릭하여 업로드</span> 또는 드래그 앤 드롭
            </>
          )}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          지원 형식: {accept.join(', ')} (최대 {formatFileSize(maxSize)})
        </p>
      </div>

      {/* 업로드된 파일 목록 */}
      {value.length > 0 && (
        <div className="mt-3 space-y-2">
          {value.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* 미리보기 */}
      {preview && (
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-1">미리보기 (첫 10줄)</p>
          <pre className="p-3 bg-gray-900 text-gray-300 text-xs rounded-lg overflow-auto max-h-40">
            {preview}
          </pre>
        </div>
      )}

      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
    </div>
  );
}
