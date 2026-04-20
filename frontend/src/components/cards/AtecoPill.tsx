export function AtecoPill({ code }: { code: string }) {
  return (
    <span className="inline-flex items-center rounded-[4px] bg-[#f6f9fc] px-[7px] py-[2px] font-mono text-[11.5px] text-[#475569]">
      ATECO <span className="tnum ml-1">{code}</span>
    </span>
  );
}
