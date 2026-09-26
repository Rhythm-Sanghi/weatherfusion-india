import { WINDOWS, type TimeWindowValue } from "./time-window";

export function TimeWindow({
  value,
  onChange,
}: {
  value: TimeWindowValue;
  onChange: (value: TimeWindowValue) => void;
}) {
  return (
    <div className="time-window" aria-label="Observation window">
      {WINDOWS.map((item) => (
        <button
          className={item === value ? "active" : ""}
          key={item}
          onClick={() => onChange(item)}
        >
          {item === "all" ? "ALL" : item.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
