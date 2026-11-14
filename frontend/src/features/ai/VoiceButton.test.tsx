// D-167: voice input starts only after a tap, and a note first says the browser may send the audio to its provider.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsProvider } from '../../app/settings';
import { vi as text } from '../../i18n/vi';
import { VoiceButton } from './VoiceButton';

const setup = (listening = false) => {
  const listen = vi.fn();
  const stop = vi.fn();
  render(<SettingsProvider><VoiceButton listening={listening} listen={listen} stop={stop} /></SettingsProvider>);
  return { listen, stop };
};

describe('voice button', () => {
  afterEach(cleanup);
  it('does not listen on its own', () => {
    const { listen } = setup();
    expect(listen).not.toHaveBeenCalled();
    expect(screen.queryByText(text.copilot.micNote)).toBeNull();
  });
  it('shows the provider note on the first tap and listens only after the second', async () => {
    const { listen } = setup();
    await userEvent.click(screen.getByRole('button', { name: text.copilot.speak }));
    expect(screen.getByText(text.copilot.micNote)).toBeTruthy();
    expect(listen).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: text.copilot.micStart }));
    expect(listen).toHaveBeenCalledTimes(1);
  });
  it('stops while listening', async () => {
    const { stop } = setup(true);
    await userEvent.click(screen.getByRole('button', { name: text.copilot.listening }));
    expect(stop).toHaveBeenCalledTimes(1);
  });
});
