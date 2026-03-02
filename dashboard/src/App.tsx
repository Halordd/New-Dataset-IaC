import AnomalyResearchCenter from './AnomalyResearchCenter'

function App() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#F5EDDC', 
      padding: '40px',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <header style={{ marginBottom: '60px', borderBottom: '1px solid rgba(0,0,0,0.1)', paddingBottom: '20px' }}>
        <div style={{ fontSize: '0.7rem', color: '#802520', fontWeight: 900, letterSpacing: '0.3em', marginBottom: '10px' }}>
          [ THESIS_PROJECT // ARC_FACILITY ]
        </div>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 900, color: '#181818', margin: 0, letterSpacing: '-0.01em', lineHeight: 1.2 }}>
          RESEARCH AND APPLYING AI TO MONITOR AND DETECT <br />
          <span style={{ color: '#802520' }}>ABNORMAL BEHAVIOR IN CLOUD INFRASTRUCTURE DEPLOYMENT VIA IAC</span>
        </h1>
        <p style={{ marginTop: '15px', fontSize: '0.85rem', color: 'rgba(0,0,0,0.6)', maxWidth: '800px', lineHeight: 1.6 }}>
          An automated analytical framework designed to identify contextual drift and configuration anomalies 
          using unsupervised machine learning within Terraform environments.
        </p>
      </header>

      <main>
        <AnomalyResearchCenter />
      </main>

      <footer style={{ marginTop: '80px', paddingTop: '40px', borderTop: '1px solid rgba(0,0,0,0.1)', textAlign: 'center' }}>
        <div style={{ fontSize: '0.6rem', color: 'rgba(0,0,0,0.4)', fontWeight: 900, letterSpacing: '0.2em' }}>
          © 2026 RHINE_LAB // ARC_FACILITY // MISSION_STABLE
        </div>
      </footer>
    </div>
  )
}

export default App
