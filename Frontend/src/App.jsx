import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL 

function App() {
  const [file, setFile] = useState(null)        // Feltöltött PDF fájl
  const [loading, setLoading] = useState(false) // Folyamatban van-e az elemzés
  const [error, setError] = useState(null)      // Hibaüzenet tárolása
  const [results, setResults] = useState(null)  // Elemzési eredmények

  // Fájl feltöltés kezelése (drag & drop vagy kattintás)
  const onDrop = useCallback((acceptedFiles) => {
    const uploadedFile = acceptedFiles[0]
    if (uploadedFile) {
      setFile(uploadedFile)
      setError(null)
      setResults(null)
    }
  }, [])

  // React-dropzone konfiguráció
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']  // Csak PDF fájlok
    },
    multiple: false,                // Egyetlen fájl egyszerre
    maxSize: 10 * 1024 * 1024       // Maximum 10 MB
  })

  // PDF elemzés küldése a backend-nek
  const analyzePDF = async () => {
    if (!file) return

    setLoading(true)
    setError(null)
    setResults(null)

    // FormData objektum létrehozása a fájl feltöltéshez
    const formData = new FormData()
    formData.append('file', file)

    try {
      // POST kérés a backend /api/analyze végpontra
      const response = await axios.post(`${API_URL}/api/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 60000 // 60 másodperc timeout
      })

      setResults(response.data)
    } catch (err) {
      console.error('Error analyzing PDF:', err)
      setError({
        message: err.response?.data?.detail || err.message || 'Hiba történt a PDF feldolgozása során',
        detail: err.response?.data?.error
      })
    } finally {
      setLoading(false)
    }
  }

  // Űrlap visszaállítása alapállapotba
  const reset = () => {
    setFile(null)
    setResults(null)
    setError(null)
  }

  // Fájlméret formázása olvasható formátumra
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="app">
      <header className="header">
        <h1>PDF Allergén & Tápérték Elemző</h1>
        <p>Töltsd fel az élelmiszer termékleírás PDF-et az elemzéshez</p>
      </header>

      <main className="main-content">
        {/* Fájl feltöltő szekció - csak akkor látszik, ha nincs eredmény */}
        {!results && (
          <div className="upload-section">
            {/* Drag & Drop terület */}
            <div
              {...getRootProps()}
              className={`dropzone ${isDragActive ? 'active' : ''}`}
            >
              <input {...getInputProps()} />
              <h3>
                {isDragActive
                  ? 'Húzd ide a PDF fájlt...'
                  : 'Kattints vagy húzd ide a PDF fájlt'}
              </h3>
            </div>

            {/* Feltöltött fájl részletei */}
            {file && (
              <div className="file-info">
                <div className="file-details">
                  <div className="file-name">{file.name}</div>
                  <div className="file-size">{formatFileSize(file.size)}</div>
                </div>
              </div>
            )}

            {/* Elemzés és törlés gombok */}
            {file && (
              <div className="button-group">
                <button
                  className="button"
                  onClick={analyzePDF}
                  disabled={loading}
                >
                  {loading ? ' Feldolgozás...' : ' Elemzés indítása'}
                </button>
                <button
                  className="button button-secondary"
                  onClick={reset}
                  disabled={loading}
                >
                  Törlés
                </button>
              </div>
            )}
          </div>
        )}

        {/* Betöltési állapot - spinner animáció */}
        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>PDF feldolgozása folyamatban... Ez eltarthat néhány másodpercig.</p>
          </div>
        )}

        {/* Hibaüzenet megjelenítése */}
        {error && (
          <div className="error">
            <h4> Hiba történt</h4>
            <p>{error.message}</p>
            {error.detail && <p><small>{error.detail}</small></p>}
            <button className="button" onClick={reset} style={{ marginTop: '1rem' }}>
              Újra próbálom
            </button>
          </div>
        )}

        {/* Elemzési eredmények megjelenítése */}
        {results && (
          <div className="results">
            <div className="results-header">
              <h2>Elemzés eredménye</h2>
            </div>

            <div className="results-grid">
              {/* Allergének lista */}
              <div className="result-card">
                <h3>
                  Allergének
                </h3>
                <div className="allergen-list">
                  {results.data?.allergens && Object.entries(results.data.allergens).length > 0 ? (
                    Object.entries(results.data.allergens).map(([name, present], index) => (
                      <div key={index} className="allergen-item">
                        <span className="allergen-name">{name}</span>
                        <span className={`allergen-status ${present ? 'present' : 'absent'}`}>
                          {present ? ' Tartalmaz' : ' Nem tartalmaz'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">Nem található allergén információ</p>
                  )}
                </div>
              </div>

              {/* Tápértékek lista */}
              <div className="result-card">
                <h3>
                  Tápértékek (100g-ra)
                </h3>
                <div className="nutrition-list">
                  {results.data?.nutrition && Object.entries(results.data.nutrition).length > 0 ? (
                    Object.entries(results.data.nutrition).map(([name, info], index) => (
                      <div key={index} className="nutrition-item">
                        <span className="nutrition-name">{name}</span>
                        <span className="nutrition-value">
                          {info?.per_100g 
                            ? `${info.per_100g} ${info.unit || 'g'}` 
                            : 'Nincs adat'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">Nem található tápérték információ</p>
                  )}
                </div>
              </div>
            </div>

            {/* Új elemzés indítása gomb */}
            <button
              className="button"
              onClick={reset}
              style={{ marginTop: '2rem' }}
            >
              Új elemzés
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
