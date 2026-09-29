import { useState, useEffect, useCallback, useTransition } from 'react';

export function useReports(filters) {
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [, startTransition] = useTransition();

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', '1');
      params.append('page_size', '100'); // fetch up to 100 items (backend max)

      if (filters.status) params.append('status', filters.status);
      if (filters.event) params.append('event', filters.event);
      if (filters.state) params.append('state', filters.state);
      if (filters.city) params.append('city', filters.city);
      if (filters.dateFrom) {
        const d = new Date(filters.dateFrom);
        if (!isNaN(d.getTime())) params.append('date_from', d.toISOString());
      }
      if (filters.dateTo) {
        const d = new Date(filters.dateTo);
        if (!isNaN(d.getTime())) params.append('date_to', d.toISOString());
      }

      const res = await fetch(`/api/reports?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch reports: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      startTransition(() => {
        setReports(data.items || []);
        setTotal(data.total || 0);
      });
    } catch (err) {
      console.error('Error fetching reports:', err);
      setError(err.message || 'Error fetching reports');
    } finally {
      setLoading(false);
    }
  }, [filters.status, filters.event, filters.state, filters.city, filters.dateFrom, filters.dateTo]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Overall status breakdown counts
  const stats = reports.reduce(
    (acc, r) => {
      const st = r.verification_status || 'unverified';
      if (acc[st] !== undefined) acc[st] += 1;
      return acc;
    },
    { verified: 0, under_review: 0, rejected: 0, unverified: 0 }
  );

  return {
    reports,
    total,
    loading,
    error,
    refresh: fetchReports,
    stats,
  };
}
