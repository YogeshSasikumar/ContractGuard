import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText } from 'lucide-react';

export default function UploadZone({ onUpload, isUploading }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
    disabled: isUploading,
  });

  return (
    <div 
      {...getRootProps()} 
      className={`upload-zone ${isDragActive ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
      id="upload-zone"
    >
      <input {...getInputProps()} />
      <div className="upload-icon">
        {isUploading ? (
          <div className="loading-spinner" style={{ width: 28, height: 28, borderWidth: 2 }} />
        ) : (
          <Upload size={28} color="white" />
        )}
      </div>
      
      {isUploading ? (
        <>
          <h3>Analyzing your contract...</h3>
          <p>This may take a moment for large documents</p>
        </>
      ) : isDragActive ? (
        <>
          <h3>Drop your contract here</h3>
          <p>Release to start analysis</p>
        </>
      ) : (
        <>
          <h3>Upload Contract PDF</h3>
          <p>Drag and drop a PDF file, or click to browse</p>
          <p style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <FileText size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
            Accepts PDF files up to 50MB
          </p>
        </>
      )}
    </div>
  );
}
