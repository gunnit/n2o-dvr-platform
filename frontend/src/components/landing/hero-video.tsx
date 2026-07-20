"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Pause, Play } from "lucide-react";

/**
 * Ambient background loop for the landing hero. The poster renders
 * immediately and is the permanent fallback when the visitor prefers
 * reduced motion or the video fails to load; the video fades in over it
 * once it can play. A pause/play toggle (WCAG 2.2.2) renders outside the
 * aria-hidden scenery wrapper.
 */
export function HeroVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [motionAllowed, setMotionAllowed] = useState(false);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setMotionAllowed(!mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const showVideo = motionAllowed && !failed;

  function togglePlayback() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      void video.play();
    } else {
      video.pause();
    }
  }

  return (
    <>
      <div aria-hidden className="absolute inset-0 overflow-hidden">
        <Image
          src="/landing/hero-poster.jpg"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        {showVideo && (
          <video
            ref={videoRef}
            src="/landing/hero-loop.mp4"
            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-1000 ${
              ready ? "opacity-100" : "opacity-0"
            }`}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            onCanPlay={() => setReady(true)}
            onError={() => setFailed(true)}
            onPlay={() => setPaused(false)}
            onPause={() => setPaused(true)}
          />
        )}
        {/* Legibility overlays: vertical navy ramp + faint core deepening */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(6,27,49,0.45) 0%, rgba(6,27,49,0.35) 45%, rgba(6,27,49,0.78) 100%)",
          }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 60% 50% at 32% 55%, rgba(6,27,49,0.55) 0%, rgba(6,27,49,0) 70%)",
          }}
        />
      </div>
      {showVideo && ready && (
        <button
          type="button"
          onClick={togglePlayback}
          aria-label={
            paused
              ? "Riproduci il video di sfondo"
              : "Metti in pausa il video di sfondo"
          }
          className="absolute right-5 bottom-5 z-10 inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/30 text-white/80 transition-colors hover:border-white/60 hover:bg-white/10 hover:text-white"
        >
          {paused ? (
            <Play className="h-4 w-4" strokeWidth={2} />
          ) : (
            <Pause className="h-4 w-4" strokeWidth={2} />
          )}
        </button>
      )}
    </>
  );
}
