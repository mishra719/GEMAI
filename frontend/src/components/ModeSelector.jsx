import { Code2, Image, MessageSquare } from 'lucide-react';

const modes = [
  { key: 'general', label: 'General', icon: MessageSquare, color: '#3f6a56' },
  { key: 'coding', label: 'Coding', icon: Code2, color: '#26547c' },
  { key: 'image', label: 'Image', icon: Image, color: '#b8743c' },
];

export default function ModeSelector({ mode, onModeChange }) {
  return (
    <div className="mode-selector">
      {modes.map((m) => {
        const Icon = m.icon;
        return (
          <button
            key={m.key}
            className={`mode-btn ${mode === m.key ? 'active' : ''}`}
            onClick={() => onModeChange(m.key)}
            title={`${m.label} mode`}
            style={mode === m.key ? { '--mode-color': m.color } : {}}
          >
            <Icon size={16} />
            <span>{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}
