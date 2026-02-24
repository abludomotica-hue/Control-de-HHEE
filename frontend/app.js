const { useState, useEffect, useCallback } = React;

const API_URL = '/api';

// Componente de Toast
function Toast({ message, type, onClose }) {
    useEffect(() => {
        const timer = setTimeout(onClose, 3000);
        return () => clearTimeout(timer);
    }, [onClose]);

    const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
    
    return (
        <div className={`fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`}>
            {message}
        </div>
    );
}

// Componente de carga de archivos
function FileUpload({ onUploadSuccess }) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState(null);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        setIsDragging(false);
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await uploadFile(files[0]);
        }
    };

    const handleFileSelect = async (e) => {
        if (e.target.files.length > 0) {
            await uploadFile(e.target.files[0]);
        }
    };

    const uploadFile = async (file) => {
        setIsUploading(true);
        setError(null);
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData,
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                onUploadSuccess(data);
            } else {
                setError(data.detail || 'Error al procesar el archivo');
            }
        } catch (err) {
            setError('Error de conexión con el servidor');
        } finally {
            setIsUploading(false);
        }
    };

    const getFileIcon = (filename) => {
        if (filename.toLowerCase().endsWith('.pdf')) {
            return <i className="fas fa-file-pdf text-red-500 text-4xl"></i>;
        }
        return <i className="fas fa-image text-blue-500 text-4xl"></i>;
    };

    return (
        <div className="card bg-white shadow-lg">
            <div className="card-body">
                <h2 className="card-title text-xl mb-4">
                    <i className="fas fa-upload mr-2"></i>
                    Cargar Archivo
                </h2>
                
                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`dropzone rounded-lg p-12 text-center cursor-pointer ${isDragging ? 'dragover' : ''}`}
                >
                    <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,.bmp,.gif"
                        onChange={handleFileSelect}
                        className="hidden"
                        id="file-input"
                    />
                    <label htmlFor="file-input" className="cursor-pointer block">
                        {isUploading ? (
                            <div className="flex flex-col items-center">
                                <i className="fas fa-spinner loading-spinner text-4xl text-primary mb-4"></i>
                                <p className="text-gray-600">Procesando archivo...</p>
                            </div>
                        ) : (
                            <>
                                <i className="fas fa-cloud-upload-alt text-5xl text-gray-400 mb-4"></i>
                                <p className="text-lg font-medium mb-2">
                                    {isDragging ? 'Suelte el archivo aquí' : 'Arrastre y suelte un archivo'}
                                </p>
                                <p className="text-sm text-gray-500 mb-4">o haga clic para seleccionar</p>
                                <p className="text-xs text-gray-400">PDF, JPG, JPEG, PNG, BMP, GIF</p>
                            </>
                        )}
                    </label>
                </div>
                
                {error && (
                    <div className="alert alert-error mt-4">
                        <i className="fas fa-exclamation-circle mr-2"></i>
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
}

// Componente de previsualización
function PreviewForm({ preview, onConfirm, onCancel }) {
    const [isEditing, setIsEditing] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [formData, setFormData] = useState(preview);

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        
        try {
            const response = await fetch(`${API_URL}/confirmar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });
            
            const data = await response.json();
            
            if (data.duplicado) {
                alert('Este trabajo ya existe en la base de datos.');
            } else if (data.success) {
                onConfirm(data.trabajo);
            }
        } catch (err) {
            alert('Error al guardar el trabajo');
        } finally {
            setIsSubmitting(false);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('es-ES');
    };

    const formatTime = (timeStr) => {
        if (!timeStr) return '';
        return timeStr.substring(0, 5);
    };

    const renderField = (label, field, type = 'text') => {
        const value = formData[field] || '';
        
        if (!isEditing) {
            let displayValue = value;
            if (type === 'date') displayValue = formatDate(value);
            else if (type === 'time') displayValue = formatTime(value);
            
            return (
                <div className="mb-3">
                    <label className="text-xs text-gray-500 block">{label}</label>
                    <span className="font-medium">{displayValue || '-'}</span>
                </div>
            );
        }

        if (type === 'select') {
            return (
                <div className="mb-3">
                    <label className="text-xs text-gray-500 block">{label}</label>
                    <select
                        value={value}
                        onChange={(e) => handleChange(field, e.target.value)}
                        className="select select-bordered select-sm w-full"
                    >
                        <option value="Ejecutado">Ejecutado</option>
                        <option value="Pendiente">Pendiente</option>
                    </select>
                </div>
            );
        }

        return (
            <div className="mb-3">
                <label className="text-xs text-gray-500 block">{label}</label>
                <input
                    type={type}
                    value={value}
                    onChange={(e) => handleChange(field, e.target.value)}
                    className="input input-bordered input-sm w-full"
                />
            </div>
        );
    };

    return (
        <div className="card bg-white shadow-lg mt-6">
            <div className="card-body">
                <div className="flex justify-between items-start mb-4">
                    <h2 className="card-title text-xl">
                        {preview.extraccion_confiable ? (
                            <i className="fas fa-check-circle text-green-500 mr-2"></i>
                        ) : (
                            <i className="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>
                        )}
                        Previsualización
                    </h2>
                    <div className="flex gap-2">
                        <span className={`badge ${preview.extraccion_confiable ? 'badge-success' : 'badge-warning'}`}>
                            {preview.extraccion_confiable ? 'Confiable' : 'Revisar'}
                        </span>
                        {preview.incompleto && (
                            <span className="badge badge-error">Incompleto</span>
                        )}
                    </div>
                </div>

                {!preview.extraccion_confiable && (
                    <div className="alert alert-warning mb-4">
                        <i className="fas fa-exclamation-triangle mr-2"></i>
                        La extracción automática no pudo detectar todos los campos. 
                        Por favor, revise y complete los datos antes de confirmar.
                    </div>
                )}

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {renderField('Tarea Número', 'tarea_numero')}
                    {renderField('Fecha Inicio', 'fecha_inicio', 'date')}
                    {renderField('Estado', 'estado', 'select')}
                    {renderField('Cliente', 'cliente_nombre')}
                    {renderField('Categoría', 'categoria')}
                    {renderField('Hora Inicio', 'hora_inicio', 'time')}
                    {renderField('Hora Finalizada', 'hora_finalizada', 'time')}
                    <div className="mb-3">
                        <label className="text-xs text-gray-500 block">Empleado Objetivo</label>
                        <span className="font-medium text-sm">{formData.empleado_objetivo}</span>
                    </div>
                </div>

                <div className="divider"></div>

                <div className="flex justify-between">
                    <button
                        className="btn btn-outline btn-sm"
                        onClick={() => setIsEditing(!isEditing)}
                    >
                        <i className={`fas fa-${isEditing ? 'times' : 'edit'} mr-2`}></i>
                        {isEditing ? 'Cancelar Edición' : 'Editar'}
                    </button>
                    <div className="flex gap-2">
                        <button className="btn btn-outline" onClick={onCancel}>
                            Cancelar
                        </button>
                        <button 
                            className="btn btn-primary" 
                            onClick={handleSubmit}
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? (
                                <><i className="fas fa-spinner loading-spinner mr-2"></i> Guardando...</>
                            ) : (
                                <><i className="fas fa-save mr-2"></i> Confirmar y Guardar</>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Componente del Dashboard
function Dashboard() {
    const [trabajos, setTrabajos] = useState([]);
    const [estadisticas, setEstadisticas] = useState(null);
    const [clientes, setClientes] = useState([]);
    const [categorias, setCategorias] = useState([]);
    const [loading, setLoading] = useState(false);
    const [filtros, setFiltros] = useState({});
    const [trabajoToDelete, setTrabajoToDelete] = useState(null);

    const cargarDatos = useCallback(async () => {
        setLoading(true);
        
        const params = new URLSearchParams();
        Object.entries(filtros).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        
        try {
            const [trabajosRes, statsRes, clientesRes, categoriasRes] = await Promise.all([
                fetch(`${API_URL}/trabajos?${params}`),
                fetch(`${API_URL}/estadisticas?${params}`),
                fetch(`${API_URL}/clientes`),
                fetch(`${API_URL}/categorias`),
            ]);
            
            if (trabajosRes.ok) setTrabajos(await trabajosRes.json());
            if (statsRes.ok) setEstadisticas(await statsRes.json());
            if (clientesRes.ok) setClientes(await clientesRes.json());
            if (categoriasRes.ok) setCategorias(await categoriasRes.json());
        } catch (err) {
            console.error('Error cargando datos:', err);
        } finally {
            setLoading(false);
        }
    }, [filtros]);

    useEffect(() => {
        cargarDatos();
    }, [cargarDatos]);

    const handleEliminar = async () => {
        if (!trabajoToDelete) return;
        
        try {
            const response = await fetch(`${API_URL}/trabajos/${trabajoToDelete.id}`, {
                method: 'DELETE',
            });
            
            if (response.ok) {
                cargarDatos();
            }
        } catch (err) {
            console.error('Error eliminando:', err);
        }
        setTrabajoToDelete(null);
    };

    const handleExportar = (formato) => {
        const params = new URLSearchParams();
        Object.entries(filtros).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });
        window.open(`${API_URL}/export/${formato}?${params}`, '_blank');
    };

    const formatDate = (dateStr) => {
        return new Date(dateStr).toLocaleDateString('es-ES');
    };

    const formatTime = (timeStr) => {
        if (!timeStr) return '-';
        return timeStr.substring(0, 5);
    };

    return (
        <div className="space-y-6">
            {/* Estadísticas */}
            {estadisticas && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="stat bg-white rounded-lg shadow p-4">
                        <div className="stat-title text-gray-500">Total Trabajos</div>
                        <div className="stat-value text-3xl font-bold">{estadisticas.total}</div>
                    </div>
                    <div className="stat bg-white rounded-lg shadow p-4">
                        <div className="stat-title text-gray-500">Ejecutados</div>
                        <div className="stat-value text-3xl font-bold text-green-600">{estadisticas.ejecutados}</div>
                    </div>
                    <div className="stat bg-white rounded-lg shadow p-4">
                        <div className="stat-title text-gray-500">Pendientes</div>
                        <div className="stat-value text-3xl font-bold text-yellow-600">{estadisticas.pendientes}</div>
                    </div>
                    <div className="stat bg-white rounded-lg shadow p-4">
                        <div className="stat-title text-gray-500">Incompletos</div>
                        <div className="stat-value text-3xl font-bold text-red-600">{estadisticas.incompletos}</div>
                    </div>
                </div>
            )}

            {/* Filtros */}
            <div className="card bg-white shadow-lg">
                <div className="card-body">
                    <h2 className="card-title text-lg mb-4">
                        <i className="fas fa-filter mr-2"></i>
                        Filtros
                    </h2>
                    
                    <div className="flex flex-wrap gap-2 mb-4">
                        <button 
                            className={`btn btn-sm ${filtros.periodo === 'dia' ? 'btn-primary' : 'btn-outline'}`}
                            onClick={() => setFiltros(prev => ({ ...prev, periodo: prev.periodo === 'dia' ? '' : 'dia' }))}
                        >
                            <i className="fas fa-calendar-day mr-1"></i> Hoy
                        </button>
                        <button 
                            className={`btn btn-sm ${filtros.periodo === 'semana' ? 'btn-primary' : 'btn-outline'}`}
                            onClick={() => setFiltros(prev => ({ ...prev, periodo: prev.periodo === 'semana' ? '' : 'semana' }))}
                        >
                            <i className="fas fa-calendar-week mr-1"></i> Esta Semana
                        </button>
                        <button 
                            className={`btn btn-sm ${filtros.periodo === 'mes' ? 'btn-primary' : 'btn-outline'}`}
                            onClick={() => setFiltros(prev => ({ ...prev, periodo: prev.periodo === 'mes' ? '' : 'mes' }))}
                        >
                            <i className="fas fa-calendar-alt mr-1"></i> Este Mes
                        </button>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <label className="label-text">Fecha Desde</label>
                            <input
                                type="date"
                                className="input input-bordered input-sm w-full"
                                value={filtros.fecha_desde || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, fecha_desde: e.target.value }))}
                            />
                        </div>
                        <div>
                            <label className="label-text">Fecha Hasta</label>
                            <input
                                type="date"
                                className="input input-bordered input-sm w-full"
                                value={filtros.fecha_hasta || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, fecha_hasta: e.target.value }))}
                            />
                        </div>
                        <div>
                            <label className="label-text">Estado</label>
                            <select
                                className="select select-bordered select-sm w-full"
                                value={filtros.estado || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, estado: e.target.value }))}
                            >
                                <option value="">Todos</option>
                                <option value="Ejecutado">Ejecutado</option>
                                <option value="Pendiente">Pendiente</option>
                            </select>
                        </div>
                        <div>
                            <label className="label-text">Cliente</label>
                            <select
                                className="select select-bordered select-sm w-full"
                                value={filtros.cliente_nombre || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, cliente_nombre: e.target.value }))}
                            >
                                <option value="">Todos</option>
                                {clientes.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="label-text">Categoría</label>
                            <select
                                className="select select-bordered select-sm w-full"
                                value={filtros.categoria || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, categoria: e.target.value }))}
                            >
                                <option value="">Todas</option>
                                {categorias.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="label-text">Tarea Número</label>
                            <input
                                type="text"
                                placeholder="Buscar..."
                                className="input input-bordered input-sm w-full"
                                value={filtros.tarea_numero || ''}
                                onChange={(e) => setFiltros(prev => ({ ...prev, tarea_numero: e.target.value }))}
                            />
                        </div>
                    </div>

                    <div className="flex justify-between items-center mt-4 pt-4 border-t">
                        <div className="flex gap-2">
                            <button className="btn btn-outline btn-sm" onClick={() => setFiltros({})}>
                                <i className="fas fa-undo mr-1"></i> Limpiar
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={cargarDatos} disabled={loading}>
                                <i className={`fas fa-sync mr-1 ${loading ? 'loading-spinner' : ''}`}></i> Actualizar
                            </button>
                        </div>
                        <div className="flex gap-2">
                            <button className="btn btn-outline btn-sm" onClick={() => handleExportar('csv')}>
                                <i className="fas fa-file-csv mr-1"></i> CSV
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={() => handleExportar('xlsx')}>
                                <i className="fas fa-file-excel mr-1"></i> Excel
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={() => handleExportar('json')}>
                                <i className="fas fa-file-code mr-1"></i> JSON
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabla */}
            <div className="card bg-white shadow-lg">
                <div className="card-body">
                    <h2 className="card-title text-lg mb-4">
                        <i className="fas fa-table mr-2"></i>
                        Trabajos ({trabajos.length})
                    </h2>
                    
                    <div className="overflow-x-auto">
                        <table className="table table-zebra w-full">
                            <thead>
                                <tr>
                                    <th>Fecha</th>
                                    <th>Tarea</th>
                                    <th>Cliente</th>
                                    <th>Estado</th>
                                    <th>Categoría</th>
                                    <th>Hora Inicio</th>
                                    <th>Hora Fin</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trabajos.length === 0 ? (
                                    <tr>
                                        <td colSpan="8" className="text-center py-8 text-gray-500">
                                            No hay trabajos registrados
                                        </td>
                                    </tr>
                                ) : (
                                    trabajos.map((trabajo) => (
                                        <tr key={trabajo.id}>
                                            <td>{formatDate(trabajo.fecha_inicio)}</td>
                                            <td className="font-medium">{trabajo.tarea_numero}</td>
                                            <td>{trabajo.cliente_nombre}</td>
                                            <td>
                                                <span className={`badge ${trabajo.estado === 'Ejecutado' ? 'badge-success' : 'badge-warning'}`}>
                                                    {trabajo.estado}
                                                </span>
                                            </td>
                                            <td>{trabajo.categoria || '-'}</td>
                                            <td>{formatTime(trabajo.hora_inicio)}</td>
                                            <td>{formatTime(trabajo.hora_finalizada)}</td>
                                            <td>
                                                <button 
                                                    className="btn btn-ghost btn-xs text-red-500"
                                                    onClick={() => setTrabajoToDelete(trabajo)}
                                                >
                                                    <i className="fas fa-trash"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Modal de confirmación */}
            {trabajoToDelete && (
                <div className="modal modal-open">
                    <div className="modal-box">
                        <h3 className="font-bold text-lg">Confirmar Eliminación</h3>
                        <p className="py-4">
                            ¿Está seguro de que desea eliminar el trabajo 
                            <strong> {trabajoToDelete.tarea_numero}</strong>?
                        </p>
                        <div className="modal-action">
                            <button className="btn btn-outline" onClick={() => setTrabajoToDelete(null)}>
                                Cancelar
                            </button>
                            <button className="btn btn-error" onClick={handleEliminar}>
                                <i className="fas fa-trash mr-1"></i> Eliminar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// App principal
function App() {
    const [activeTab, setActiveTab] = useState('upload');
    const [uploadResponse, setUploadResponse] = useState(null);

    const handleUploadSuccess = (response) => {
        setUploadResponse(response);
    };

    const handleConfirm = () => {
        setUploadResponse(null);
        setActiveTab('dashboard');
    };

    const handleCancel = () => {
        setUploadResponse(null);
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center gap-3">
                        <div className="bg-primary text-white p-2 rounded-lg">
                            <i className="fas fa-clipboard-list text-2xl"></i>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">Work Tracker</h1>
                            <p className="text-sm text-gray-500">Control de Trabajos por Día, Semana y Mes</p>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-6">
                {/* Tabs */}
                <div className="tabs tabs-boxed justify-center mb-6 bg-white p-2 rounded-lg shadow-sm inline-flex w-full max-w-md mx-auto block">
                    <button 
                        className={`tab ${activeTab === 'upload' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('upload')}
                    >
                        <i className="fas fa-upload mr-2"></i> Cargar Archivo
                    </button>
                    <button 
                        className={`tab ${activeTab === 'dashboard' ? 'tab-active' : ''}`}
                        onClick={() => setActiveTab('dashboard')}
                    >
                        <i className="fas fa-chart-bar mr-2"></i> Dashboard
                    </button>
                </div>

                {/* Content */}
                {activeTab === 'upload' && (
                    <div className="max-w-2xl mx-auto">
                        <FileUpload onUploadSuccess={handleUploadSuccess} />
                        {uploadResponse && (
                            <PreviewForm
                                preview={uploadResponse.preview}
                                onConfirm={handleConfirm}
                                onCancel={handleCancel}
                            />
                        )}
                    </div>
                )}

                {activeTab === 'dashboard' && <Dashboard />}
            </main>

            {/* Footer */}
            <footer className="bg-white border-t mt-auto">
                <div className="container mx-auto px-4 py-4">
                    <p className="text-center text-sm text-gray-500">
                        Work Tracker - Sistema de Control de Trabajos
                    </p>
                </div>
            </footer>
        </div>
    );
}

// Renderizar
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
