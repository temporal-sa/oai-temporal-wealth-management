import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the chat with a Start Chat button', () => {
  render(<App />);
  expect(screen.getByRole('button', { name: 'Start Chat' })).toBeInTheDocument();
  expect(screen.getByPlaceholderText('Type a message...')).toBeDisabled();
});
