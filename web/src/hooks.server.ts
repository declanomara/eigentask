export const handleError = ({ error, event }) => {
  console.error('handleError', {
    path: event.url.pathname,
    message: (error as any)?.message,
    stack: (error as any)?.stack
  });
};