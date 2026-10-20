"use client";

import { useEffect, useRef } from 'react';

export default function AccountOrbit() {
  const scene = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scene.current;
    if (!element) return;
    let visible = false;
    const update = () => { element.dataset.motion = visible && !document.hidden ? 'running' : 'paused'; };
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      update();
    }, { rootMargin: '80px' });
    observer.observe(element);
    document.addEventListener('visibilitychange', update);
    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', update);
    };
  }, []);

  return (
    <div className="account-orbit" ref={scene} data-motion="paused" aria-hidden="true">
      <div className="account-orbit-halo" />
      <div className="account-orbit-float">
        <div className="account-orbit-core" />
        <div className="account-orbit-cage">
          <span className="account-orbit-ring account-orbit-ring-one"><i /></span>
          <span className="account-orbit-ring account-orbit-ring-two"><i /></span>
          <span className="account-orbit-ring account-orbit-ring-three"><i /></span>
          <span className="account-orbit-ring account-orbit-ring-four" />
          <span className="account-orbit-ring account-orbit-ring-five" />
        </div>
      </div>
      <div className="account-orbit-shadow" />
    </div>
  );
}
