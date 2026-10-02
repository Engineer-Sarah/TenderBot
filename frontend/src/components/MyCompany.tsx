import { useState, useRef, useCallback } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  Building2,
  MapPin,
  Briefcase,
  Wallet,
  CloudUpload,
  FileCheck,
} from 'lucide-react';
import type { UploadedFile, CompanyProfile } from '../types';
import { formatBytes } from '../utils/helpers';

interface MyCompanyProps {
  profile: CompanyProfile;
  uploadedFiles: UploadedFile[];
  onAddFiles: (files: File[]) => void;
  onDeleteFile: (id: string) => void;
}

export function MyCompany({ profile, uploadedFiles, onAddFiles, onDeleteFile }: MyCompanyProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        setIsUploading(true);
        setTimeout(() => {
          onAddFiles(files);
          setIsUploading(false);
        }, 600);
      }
    },
    [onAddFiles]
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setIsUploading(true);
      setTimeout(() => {
        onAddFiles(files);
        setIsUploading(false);
      }, 600);
    }
    e.target.value = '';
  };

  const requiredDocs = [
    { name: 'NTN Certificate', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('ntn')) },
    { name: 'Company Registration', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('registration') || f.name.toLowerCase().includes('company')) },
    { name: 'Financial Statements', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('financial')) },
    { name: 'ISO Certification', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('iso')) },
    { name: 'PSEB Registration', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('pseb')) },
    { name: 'Bid Security', uploaded: uploadedFiles.some((f) => f.name.toLowerCase().includes('bid') || f.name.toLowerCase().includes('security')) },
  ];

  const uploadedCount = requiredDocs.filter((d) => d.uploaded).length;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">My Company</h2>
        <p className="text-sm text-muted mt-1">Manage your company profile and tender documents</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Company Profile */}
        <div className="bg-card rounded-xl border border-edge shadow-sm p-6 h-fit">
          <div className="flex items-center gap-3 mb-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500 text-white">
              <Building2 className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-bold text-ink">{profile.name}</h3>
              <p className="text-xs text-muted">Verified Company</p>
            </div>
          </div>

          <div className="space-y-3">
            <ProfileRow icon={<Briefcase className="h-4 w-4" />} label="Industries" value={profile.industries.join(', ')} />
            <ProfileRow icon={<MapPin className="h-4 w-4" />} label="Location" value={profile.location} />
            <ProfileRow icon={<Wallet className="h-4 w-4" />} label="Budget Range" value={profile.budgetRange} />
          </div>

          {/* Document Checklist */}
          <div className="mt-6 pt-5 border-t border-edge">
            <h4 className="text-xs font-semibold text-muted uppercase tracking-wide mb-3">Document Checklist</h4>
            <div className="space-y-2">
              {requiredDocs.map((doc) => (
                <div key={doc.name} className="flex items-center gap-2 text-sm">
                  {doc.uploaded ? (
                    <CheckCircle2 className="h-4 w-4 text-success-500 flex-shrink-0" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border-2 border-edge flex-shrink-0" />
                  )}
                  <span className={doc.uploaded ? 'text-ink' : 'text-muted'}>{doc.name}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 px-3 py-2 rounded-lg bg-primary-50 border border-primary-100">
              <p className="text-xs text-primary-700">
                <span className="font-bold">{uploadedCount}/{requiredDocs.length}</span> key documents uploaded
              </p>
            </div>
          </div>
        </div>

        {/* Upload Area + File List */}
        <div className="lg:col-span-2 space-y-6">
          {/* Drag & Drop */}
          <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <CloudUpload className="h-5 w-5 text-primary-600" />
              <h3 className="font-bold text-ink">Upload Documents</h3>
            </div>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={[
                'relative rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer',
                'flex flex-col items-center justify-center py-12 px-6 text-center',
                isDragging
                  ? 'border-primary-500 bg-primary-50 scale-[1.01]'
                  : 'border-edge hover:border-primary-400 hover:bg-primary-50/30',
              ].join(' ')}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
              />

              {isUploading ? (
                <>
                  <div className="h-12 w-12 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin mb-3" />
                  <p className="text-sm font-medium text-ink">Uploading files...</p>
                  <p className="text-xs text-muted mt-1">Please wait</p>
                </>
              ) : (
                <>
                  <div className={[
                    'flex h-14 w-14 items-center justify-center rounded-full mb-3 transition-all',
                    isDragging ? 'bg-primary-500 scale-110' : 'bg-primary-100',
                  ].join(' ')}>
                    <Upload className={[
                      'h-6 w-6 transition-colors',
                      isDragging ? 'text-white' : 'text-primary-600',
                    ].join(' ')} />
                  </div>
                  <p className="text-sm font-medium text-ink">
                    {isDragging ? 'Drop files here to upload' : 'Drag & drop files here, or click to browse'}
                  </p>
                  <p className="text-xs text-muted mt-1">
                    Supports PDF, DOC, DOCX, XLS, XLSX, PNG, JPG
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Uploaded Files List */}
          <div className="bg-card rounded-xl border border-edge shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-primary-600" />
                <h3 className="font-bold text-ink">Uploaded Files</h3>
              </div>
              <span className="text-xs font-medium text-muted bg-primary-50 px-2.5 py-1 rounded-full">
                {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''}
              </span>
            </div>

            {uploadedFiles.length === 0 ? (
              <div className="py-8 text-center">
                <FileText className="h-10 w-10 text-primary-300 mx-auto mb-2" />
                <p className="text-sm text-muted">No files uploaded yet</p>
                <p className="text-xs text-muted mt-1">Upload documents to prepare for tender submissions</p>
              </div>
            ) : (
              <div className="space-y-2">
                {uploadedFiles.map((file, index) => (
                  <div
                    key={file.id}
                    className="flex items-center gap-3 px-4 py-3 rounded-lg border border-edge hover:border-primary-300 hover:bg-primary-50/20 transition-all group animate-slide-up"
                    style={{ animationDelay: `${index * 40}ms` }}
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 text-primary-600 flex-shrink-0">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-ink truncate">{file.name}</p>
                      <p className="text-xs text-muted">
                        {formatBytes(file.size)} &middot; Uploaded {file.uploadDate}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <span className="hidden sm:flex items-center gap-1 text-xs text-success-600 mr-2">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Ready
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteFile(file.id);
                        }}
                        className="p-2 rounded-lg text-muted hover:text-error-600 hover:bg-error-50 transition-colors"
                        aria-label={`Delete ${file.name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50 text-muted flex-shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted">{label}</p>
        <p className="text-sm font-medium text-ink">{value}</p>
      </div>
    </div>
  );
}
