(() => {
  const findInput = () => {
    return (
      document.querySelector('#chat-input textarea') ||
      document.querySelector('#chat-input input') ||
      document.querySelector('textarea#chat-input') ||
      document.querySelector('input#chat-input') ||
      document.querySelector('#chat-input [contenteditable="true"]')
    );
  };

  const setValue = (el, value) => {
    if (!el) return false;

    if (el.isContentEditable) {
      el.textContent = value;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.focus();
      return true;
    }

    const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
    if (descriptor && typeof descriptor.set === 'function') {
      descriptor.set.call(el, value);
    } else {
      el.value = value;
    }

    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.focus();
    return true;
  };

  const setDisabled = (disabled) => {
    const el = findInput();
    if (!el) return false;
    if (el.isContentEditable) {
      el.setAttribute('contenteditable', disabled ? 'false' : 'true');
    } else {
      el.disabled = !!disabled;
    }
    return true;
  };

  const trySetInput = (value) => {
    const el = findInput();
    return setValue(el, value);
  };

  window.addEventListener('message', (event) => {
    const data = event?.data;
    if (!data) return;

    if (data.type === 'set_chat_input') {
      const value = typeof data.value === 'string' ? data.value : '';

      if (!trySetInput(value)) {
        let attempts = 0;
        const interval = setInterval(() => {
          attempts += 1;
          if (trySetInput(value) || attempts >= 10) {
            clearInterval(interval);
          }
        }, 150);
      }
      return;
    }

    if (data.type === 'set_input_disabled') {
      const disabled = !!data.value;
      if (!setDisabled(disabled)) {
        let attempts = 0;
        const interval = setInterval(() => {
          attempts += 1;
          if (setDisabled(disabled) || attempts >= 10) {
            clearInterval(interval);
          }
        }, 150);
      }
    }
  });
})();
