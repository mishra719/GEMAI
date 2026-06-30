import SyntaxHighlighter from 'react-syntax-highlighter/dist/esm/prism-async-light';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function CodeBlock({ language, code, customStyle, ...props }) {
  return (
    <SyntaxHighlighter
      style={oneDark}
      language={language}
      PreTag="div"
      customStyle={customStyle}
      {...props}
    >
      {code}
    </SyntaxHighlighter>
  );
}
