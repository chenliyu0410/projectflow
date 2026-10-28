import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import LoginScreen, { departureMs } from './components/LoginScreen';

const props = { organization: 'food', username: 'yu', password: '', onOrganization: vi.fn(), onUsername: vi.fn(), onPassword: vi.fn(), busy: false, message: '', leaving: false, onSubmit: vi.fn((e: { preventDefault: () => void }) => e.preventDefault()) };

it('shows the water login card with the brand, fields and submit button', () => {
  render(<LoginScreen {...props} password="demo-yu" />);
  expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  expect(screen.getByText('讓每一件工作，順著流程走到底。')).toBeInTheDocument();
  expect(screen.getByLabelText('公司')).toHaveValue('food');
  expect(screen.getByLabelText('帳號')).toHaveValue('yu');
  expect(screen.getByLabelText('密碼')).toHaveAttribute('type', 'password');
  fireEvent.change(screen.getByLabelText('帳號'), { target: { value: 'ming' } });
  expect(props.onUsername).toHaveBeenCalledWith('ming');
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
  expect(props.onSubmit).toHaveBeenCalledOnce();
  // The prototype's hint line and welcome screen are not part of the product.
  expect(screen.queryByText(/原型/)).toBeNull();
  expect(screen.queryByText('歡迎回來')).toBeNull();
});

it('shows the error inside the card and sways it, then sinks the card while leaving', () => {
  const view = render(<LoginScreen {...props} />);
  view.rerender(<LoginScreen {...props} message="帳號或密碼錯誤" />);
  expect(screen.getByRole('alert')).toHaveTextContent('帳號或密碼錯誤');
  const card = document.querySelector('.wl-card')!;
  expect(card).toHaveClass('sway');
  view.rerender(<LoginScreen {...props} busy leaving />);
  expect(card).toHaveClass('sink');
  expect(screen.getByRole('button', { name: '登入中' })).toBeDisabled();
  expect(screen.getByLabelText('密碼')).toBeDisabled();
});

it('does not hold up sign-in when the water cannot be drawn', () => {
  render(<LoginScreen {...props} />);
  // jsdom has no WebGL, so the departure animation is skipped.
  expect(departureMs()).toBe(0);
});
