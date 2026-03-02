import { useState, useEffect, useMemo } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend } from 'recharts';
import { ListFilter, AlertTriangle, ExternalLink, HelpCircle, BookOpen, Target, Activity } from 'lucide-react';

const ARC_DATA_URL = '/data/arc_master_data.json';

const InfoTooltip = ({ title, content, visible }: { title: string, content: string, visible?: boolean }) => (
  <div style={{ 
    position: 'absolute', zIndex: 100, background: '#181818', border: '1px solid #BA8530', 
    padding: '12px', width: '220px', borderRadius: '2px', boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
    display: visible ? 'block' : 'none', pointerEvents: 'none', top: '100%', left: '0', marginTop: '10px'
  }}>
    <div style={{ color: '#BA8530', fontSize: '0.65rem', fontWeight: 900, marginBottom: '5px', letterSpacing: '0.1em' }}>[ GUIDANCE: {title} ]</div>
    <div style={{ color: 'white', fontSize: '0.65rem', lineHeight: 1.4, opacity: 0.9 }}>{content}</div>
  </div>
);

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div style={{ background: 'rgba(24, 24, 24, 0.98)', border: '1px solid #802520', padding: '12px', color: 'white', fontFamily: 'monospace', fontSize: '0.7rem', boxShadow: '0 10px 30px rgba(0,0,0,0.5)', zIndex: 1000 }}>
        <p style={{ color: '#BA8530', marginBottom: '4px', fontWeight: 'bold' }}>[ID: String(data.id || '').split(':')[0]]</p>
        <p style={{ fontWeight: 900, marginBottom: '4px' }}>{String(data.name || '').split('/').pop()}</p>
        <p>SCORE: {data.score?.toFixed(4)}</p>
        <p>CONTEXT: {data.context}</p>
      </div>
    );
  }
  return null;
};

const AnomalyResearchCenter = () => {
  const [data, setData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [activeContexts, setActiveContexts] = useState<string[]>([]);
  const [threshold, setThreshold] = useState<number>(0.35);
  const [helpMode, setHelpMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(ARC_DATA_URL)
      .then(res => res.json())
      .then(json => {
        setData(json);
        setSelectedNode(json.nodes[0]);
        setActiveContexts(json.contexts.map((c: any) => c.context_id));
        if (json.metadata?.model_metrics?.suggested_threshold_for_reporting) {
          setThreshold(json.metadata.model_metrics.suggested_threshold_for_reporting);
        }
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const processedNodes = useMemo(() => {
    if (!data) return [];
    return data.nodes.map((n: any) => ({
      ...n,
      dynamicLabel: n.score >= threshold ? 'anomaly' : 'normal'
    }));
  }, [data, threshold]);

  const filteredNodes = useMemo(() => {
    return processedNodes.filter((n: any) => activeContexts.includes(n.context));
  }, [processedNodes, activeContexts]);

  const topAnomalies = useMemo(() => {
    return [...processedNodes]
      .filter((n: any) => n.dynamicLabel === 'anomaly')
      .sort((a, b) => b.score - a.score)
      .slice(0, 15);
  }, [processedNodes]);

  const anomalyDrivers = useMemo(() => {
    if (!selectedNode?.drift) return [];
    return Object.entries(selectedNode.drift)
      .sort(([, a]: any, [, b]: any) => Math.abs(b) - Math.abs(a))
      .slice(0, 3)
      .map(([key, val]: any) => ({
        feature: key.replace('_count', ''),
        drift: val
      }));
  }, [selectedNode]);

  const radarData = useMemo(() => {
    if (!selectedNode || !data) return [];
    const contextMeta = data.contexts.find((c: any) => c.context_id === selectedNode.context);
    return Object.keys(data.metadata.feature_groups).map(group => {
      const features = data.metadata.feature_groups[group];
      const sampleVal = features.reduce((acc: number, f: string) => acc + (selectedNode.features?.[f] || 0), 0);
      const baselineVal = features.reduce((acc: number, f: string) => acc + (contextMeta?.baseline_features?.[f] || 0), 0);
      return { subject: group, sample: sampleVal, baseline: baselineVal };
    });
  }, [selectedNode, data]);

  if (loading) return <div style={{ padding: '100px', textAlign: 'center', fontFamily: 'monospace' }}>{">"} INITIALIZING_GUIDANCE_SYSTEM...</div>;
  if (error) return <div style={{ color: '#802520', padding: '40px' }}>[ ERROR: {error} ]</div>;

  return (
    <div className="arc-dashboard" style={{ display: 'flex', flexDirection: 'column', gap: '30px', position: 'relative' }}>
      
      {/* HELP MODE TOGGLE */}
      <button 
        onClick={() => setHelpMode(!helpMode)}
        style={{ 
          position: 'fixed', bottom: '100px', right: '40px', zIndex: 1000, 
          background: helpMode ? '#BA8530' : '#181818', color: helpMode ? 'black' : 'white',
          border: '1px solid #BA8530', padding: '12px 20px', borderRadius: '30px',
          display: 'flex', alignItems: 'center', gap: '10px', fontWeight: 900, fontSize: '0.7rem',
          cursor: 'pointer', boxShadow: '0 10px 30px rgba(0,0,0,0.3)', transition: 'all 0.3s'
        }}
      >
        <HelpCircle size={16} /> {helpMode ? 'EXIT_HELP_MODE' : 'ACTIVATE_HELP_MODE'}
      </button>

      {/* 01 // TOP KPI BOARD */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
        <div style={{ background: '#181818', padding: '25px', borderLeft: '4px solid #802520', position: 'relative' }}>
          <div style={{ fontSize: '0.6rem', color: '#BA8530', fontWeight: 900, letterSpacing: '0.1em' }}>THREAT_LEVEL</div>
          <div style={{ color: 'white', fontSize: '1.5rem', fontWeight: 900, marginTop: '5px' }}>
            {topAnomalies.length > 8 ? 'CRITICAL' : topAnomalies.length > 3 ? 'ELEVATED' : 'STABLE'}
          </div>
          <InfoTooltip visible={helpMode} title="THREAT_LEVEL" content="Trạng thái nguy cơ dựa trên tỷ lệ node bất thường so với quy mô hạ tầng. Màu đỏ yêu cầu can thiệp ngay." />
        </div>
        
        <div style={{ background: 'white', padding: '25px', border: '1px solid rgba(0,0,0,0.1)', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ fontSize: '0.6rem', color: '#802520', fontWeight: 900 }}>ANOMALY_THRESHOLD</div>
            <div style={{ fontSize: '0.8rem', fontWeight: 900 }}>{threshold.toFixed(3)}</div>
          </div>
          <input type="range" min="0.1" max="0.8" step="0.005" value={threshold} onChange={(e) => setThreshold(parseFloat(e.target.value))} style={{ width: '100%', accentColor: '#802520' }} />
          <InfoTooltip visible={helpMode} title="THRESHOLD" content="Kéo để chỉnh độ nhạy AI. Thấp: phát hiện mọi drift nhỏ. Cao: chỉ báo động khi sai lệch cực lớn." />
        </div>

        <div style={{ background: 'white', padding: '25px', border: '1px solid rgba(0,0,0,0.1)', position: 'relative' }}>
          <div style={{ fontSize: '0.6rem', color: '#802520', fontWeight: 900 }}>DETECTED_ANOMALIES</div>
          <div style={{ color: '#181818', fontSize: '1.5rem', fontWeight: 900, marginTop: '5px' }}>{topAnomalies.length} UNITS</div>
          <InfoTooltip visible={helpMode} title="ANOMALY_COUNT" content="Tổng số dự án IaC đang vượt ngưỡng sai lệch hành vi so với Baseline ngữ cảnh." />
        </div>
      </div>

      {/* 02 // MAIN INTERFACE GRID */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 350px', gap: '30px', minHeight: '800px' }}>
        
        {/* LEFT: FILTERS */}
        <div style={{ background: 'white', border: '1px solid rgba(0,0,0,0.1)', padding: '25px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 900, color: '#802520', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
            <ListFilter size={14} style={{ verticalAlign: 'middle', marginRight: '8px' }} /> CONTEXT_FILTER
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {data.contexts.map((ctx: any) => (
              <label key={ctx.context_id} style={{ 
                display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', marginBottom: '8px', borderRadius: '4px', cursor: 'pointer',
                background: activeContexts.includes(ctx.context_id) ? 'rgba(186, 133, 48, 0.08)' : '#f9f9f8',
                border: activeContexts.includes(ctx.context_id) ? '1px solid #BA8530' : '1px solid transparent'
              }}>
                <input type="checkbox" checked={activeContexts.includes(ctx.context_id)} onChange={() => setActiveContexts(prev => prev.includes(ctx.context_id) ? prev.filter(id => id !== ctx.context_id) : [...prev, ctx.context_id])} />
                <div style={{ fontSize: '0.75rem' }}>
                  <div style={{ fontWeight: 900 }}>{ctx.context_id}</div>
                  <div style={{ opacity: 0.5, fontSize: '0.6rem' }}>{ctx.name}</div>
                </div>
              </label>
            ))}
          </div>
          <InfoTooltip visible={helpMode} title="CONTEXTS" content="Mỗi cụm (C1-C8) đại diện cho một loại hạ tầng (VD: Serverless, Database). AI sẽ học Baseline riêng cho từng cụm này." />
        </div>

        {/* CENTER: ORBIT MAP */}
        <div style={{ background: '#fcfcfc', border: '1px solid rgba(0,0,0,0.1)', padding: '40px', position: 'relative', display: 'flex', flexDirection: 'column' }}>
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.03, background: 'repeating-linear-gradient(0deg, #000, #000 1px, transparent 1px, transparent 50px), repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 50px)' }}></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div style={{ fontSize: '0.7rem', color: '#802520', fontWeight: 900 }}>BEHAVIORAL_ORBIT_MAP</div>
            <div style={{ background: '#181818', color: 'white', padding: '10px', fontSize: '0.55rem', borderRadius: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                <span style={{ width: '8px', height: '8px', background: '#BA8530', borderRadius: '50%' }}></span> SAFE_NODE
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ width: '0', height: '0', borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderBottom: '8px solid #802520' }}></span> THREAT_NODE
              </div>
            </div>
          </div>

          <div style={{ flex: 1, minHeight: '500px', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <XAxis type="number" dataKey="x" hide domain={['auto', 'auto']} />
                <YAxis type="number" dataKey="y" hide domain={['auto', 'auto']} />
                <ZAxis type="number" dataKey="score" range={[100, 600]} />
                <line x1="50%" y1="0" x2="50%" y2="100%" stroke="#802520" strokeOpacity={0.05} strokeDasharray="5 5" />
                <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#802520" strokeOpacity={0.05} strokeDasharray="5 5" />
                <Tooltip content={<CustomTooltip />} />
                <Scatter data={filteredNodes.filter((n: any) => n.dynamicLabel === 'normal')} fill="#BA8530" shape="circle" onClick={(n) => setSelectedNode(n)} style={{ cursor: 'pointer', opacity: 0.6 }} />
                <Scatter data={filteredNodes.filter((n: any) => n.dynamicLabel === 'anomaly')} fill="#802520" shape="triangle" onClick={(n) => setSelectedNode(n)} style={{ cursor: 'pointer' }} />
              </ScatterChart>
            </ResponsiveContainer>
            <InfoTooltip visible={helpMode} title="PCA_ORBIT" content="Khoảng cách = Tương đồng cấu hình. PC1 (Ngang): Quy mô tài nguyên. PC2 (Dọc): Độ tùy biến cấu hình. Các điểm xa tâm là đối tượng bị Drift." />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', fontWeight: 900, color: '#802520', opacity: 0.3, letterSpacing: '0.2em' }}>
            <span>{"<"} LOW_STRUCTURAL_MASS</span>
            <span>HIGH_STRUCTURAL_MASS {">"}</span>
          </div>
        </div>

        {/* RIGHT: ANALYTICS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          <div style={{ background: 'white', border: '1px solid rgba(0,0,0,0.1)', padding: '25px', position: 'relative' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 900, color: '#802520', marginBottom: '15px' }}>DRIFT_EXPLANATION</div>
            <div style={{ height: '220px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#eee" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fontFamily: 'monospace' }} />
                  <Radar name="Target" dataKey="sample" stroke="#802520" fill="#802520" fillOpacity={0.4} />
                  <Radar name="Baseline" dataKey="baseline" stroke="#BA8530" fill="#BA8530" fillOpacity={0.1} strokeDasharray="4 4" />
                  <Legend iconSize={8} wrapperStyle={{ fontSize: '0.6rem', paddingTop: '10px' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ marginTop: '20px', borderTop: '1px solid #f5f5f5', paddingTop: '15px' }}>
              <div style={{ fontSize: '0.55rem', color: '#802520', fontWeight: 900, marginBottom: '10px' }}>TOP_ANOMALY_DRIVERS</div>
              {anomalyDrivers.map((d, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', padding: '6px 0', borderBottom: '1px dashed #eee' }}>
                  <span style={{ fontFamily: 'monospace' }}>{d.feature.toUpperCase()}</span>
                  <span style={{ color: d.drift > 0 ? '#f00' : '#0a0', fontWeight: 'bold' }}>{d.drift > 0 ? '+' : ''}{d.drift.toFixed(1)}</span>
                </div>
              ))}
            </div>
            <InfoTooltip visible={helpMode} title="RADAR_DRIFT" content="Vùng tô đỏ phình to hơn đường nét đứt vàng ➔ Tài nguyên IaC đang dư thừa bất thường so với trung bình ngữ cảnh." />
          </div>

          <div style={{ background: '#181818', color: 'white', padding: '25px', flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 900, color: '#BA8530' }}>PRIORITY_QUEUE</div>
              <a href={selectedNode?.url} target="_blank" rel="noreferrer" style={{ color: '#BA8530', fontSize: '0.6rem', textDecoration: 'none', border: '1px solid #BA8530', padding: '3px 10px' }}>SOURCE <ExternalLink size={10} /></a>
            </div>
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {topAnomalies.map((node: any) => (
                <div key={node.id} onClick={() => setSelectedNode(node)} style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer', background: selectedNode?.id === node.id ? 'rgba(128, 37, 32, 0.25)' : 'transparent' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 900 }}>{String(node.name).split('/').pop()}</span>
                    <span style={{ fontSize: '0.65rem', color: '#f44', fontWeight: 'bold' }}>{node.score.toFixed(3)}</span>
                  </div>
                </div>
              ))}
            </div>
            <InfoTooltip visible={helpMode} title="ALERTS" content="Danh sách các dự án có Anomaly Score cao nhất. Click để khóa mục tiêu và xem bằng chứng code." />
          </div>
        </div>
      </div>

      {/* FOOTER SYSTEM LOG */}
      <div style={{ background: '#181818', padding: '20px 40px', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #802520' }}>
        <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
          {">"} SYSTEM_MISSION: RESEARCH_AND_MONITOR_IAC_ANOMALIES<br />
          {">"} STATUS: {helpMode ? 'GUIDANCE_OVERLAY_ACTIVE' : 'DATA_STREAM_NOMINAL'}
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.65rem', color: '#BA8530', fontWeight: 'bold' }}>
          RHINE_LAB // ARC_EXPERT_SYSTEM<br />
          <span style={{ color: '#802520', letterSpacing: '0.1em' }}>v4.0.0_EXPLAINABLE_AI_STABLE</span>
        </div>
      </div>
    </div>
  );
};

export default AnomalyResearchCenter;
