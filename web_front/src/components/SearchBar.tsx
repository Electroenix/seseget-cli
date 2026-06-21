import type { FormEvent } from "react";

interface SearchBarProps {
  siteList: string[];
  onSubmit: (formData: FormData) => void;
}

export default function SearchBar({ siteList, onSubmit }: SearchBarProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    onSubmit(formData);
  };

  return (
    <div className="row justify-content-center pt-4 mb-4">
      <div className="col-md-10 col-lg-8">
        <form className="search-form" onSubmit={handleSubmit}>
          <div className="input-group input-group-lg">
            <select
              className="form-select"
              name="station"
              defaultValue=""
              style={{ maxWidth: "130px" }}
            >
              {siteList.map((site) => (
                <option key={site} value={site}>
                  {site}
                </option>
              ))}
            </select>
            <input
              type="text"
              className="form-control"
              name="url"
              placeholder="输入媒体 URL..."
            />
            <button className="btn btn-primary px-4" type="submit">
              <i className="bi bi-search me-1" />
              GET
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
