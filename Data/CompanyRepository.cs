using System;
using System.Collections.Generic;
using System.Configuration;
using System.Data;
using System.Data.SqlClient;
using NewHireCompanyManager.Models;

namespace NewHireCompanyManager.Data
{
    public class CompanyRepository
    {
        private readonly string _connectionString;

        public CompanyRepository()
            : this(ConfigurationManager.ConnectionStrings["CompanyDb"].ConnectionString)
        {
        }

        public CompanyRepository(string connectionString)
        {
            _connectionString = connectionString;
        }

        public IList<Company> GetCompanies()
        {
            var companies = new List<Company>();

            using (var connection = new SqlConnection(_connectionString))
            using (var command = new SqlCommand("dbo.uspCompany_List", connection))
            {
                command.CommandType = CommandType.StoredProcedure;
                connection.Open();

                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        companies.Add(new Company
                        {
                            CompanyIdentifier = ReadString(reader, "CompanyIdentifier"),
                            CompanyName = ReadString(reader, "CompanyName")
                        });
                    }
                }
            }

            return companies;
        }

        public Company GetCompany(string companyIdentifier)
        {
            Company company = null;

            using (var connection = new SqlConnection(_connectionString))
            using (var command = new SqlCommand("dbo.uspCompany_Get", connection))
            {
                command.CommandType = CommandType.StoredProcedure;
                command.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = companyIdentifier;
                connection.Open();

                using (var reader = command.ExecuteReader())
                {
                    if (reader.Read())
                    {
                        company = MapCompany(reader);
                    }

                    if (company != null && reader.NextResult())
                    {
                        while (reader.Read())
                        {
                            company.Modules.Add(new CompanyModule
                            {
                                Name = ReadString(reader, "ModuleName"),
                                IsEnabled = ReadBoolean(reader, "IsEnabled")
                            });
                        }
                    }
                }
            }

            return company;
        }

        public void SaveCompany(Company company, bool isNewCompany)
        {
            using (var connection = new SqlConnection(_connectionString))
            {
                connection.Open();

                using (var transaction = connection.BeginTransaction())
                {
                    try
                    {
                        SaveCompanyDetails(connection, transaction, company, isNewCompany);
                        SaveLogo(connection, transaction, company);
                        SaveModules(connection, transaction, company);
                        transaction.Commit();
                    }
                    catch
                    {
                        transaction.Rollback();
                        throw;
                    }
                }
            }
        }

        public void DeleteCompany(string companyIdentifier)
        {
            using (var connection = new SqlConnection(_connectionString))
            using (var command = new SqlCommand("dbo.uspCompany_Delete", connection))
            {
                command.CommandType = CommandType.StoredProcedure;
                command.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = companyIdentifier;
                connection.Open();
                command.ExecuteNonQuery();
            }
        }

        private void SaveCompanyDetails(SqlConnection connection, SqlTransaction transaction, Company company, bool isNewCompany)
        {
            using (var command = new SqlCommand("dbo.uspCompany_Save", connection, transaction))
            {
                command.CommandType = CommandType.StoredProcedure;
                command.Parameters.Add("@IsNewCompany", SqlDbType.Bit).Value = isNewCompany;
                command.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = company.CompanyIdentifier;
                command.Parameters.Add("@CompanyName", SqlDbType.NVarChar, 150).Value = company.CompanyName;
                AddNullable(command, "@Address1", company.Address1, 150);
                AddNullable(command, "@Address2", company.Address2, 150);
                AddNullable(command, "@City", company.City, 80);
                AddNullable(command, "@State", company.State, 2);
                AddNullable(command, "@Zip", company.Zip, 15);
                AddNullable(command, "@PhoneNumber", company.PhoneNumber, 25);
                command.Parameters.Add("@PrimaryContact", SqlDbType.NVarChar, 150).Value = company.PrimaryContact;
                command.Parameters.Add("@PointOfContactEmail", SqlDbType.NVarChar, 150).Value = company.PointOfContactEmail;
                command.Parameters.Add("@TaxId", SqlDbType.NVarChar, 25).Value = company.TaxId;
                command.Parameters.Add("@BankName", SqlDbType.NVarChar, 150).Value = company.BankName;
                command.Parameters.Add("@Form1099", SqlDbType.Bit).Value = company.Form1099;
                AddNullable(command, "@WithholdingNumber", company.WithholdingNumber, 50);
                AddNullable(command, "@County", company.County, 80);
                command.ExecuteNonQuery();
            }
        }

        private void SaveLogo(SqlConnection connection, SqlTransaction transaction, Company company)
        {
            if (company.LogoBytes == null || company.LogoBytes.Length == 0)
            {
                return;
            }

            using (var command = new SqlCommand("dbo.uspLogo_Save", connection, transaction))
            {
                command.CommandType = CommandType.StoredProcedure;
                command.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = company.CompanyIdentifier;
                command.Parameters.Add("@FileName", SqlDbType.NVarChar, 255).Value = company.LogoFileName;
                command.Parameters.Add("@ContentType", SqlDbType.NVarChar, 100).Value = company.LogoContentType;
                command.Parameters.Add("@LogoData", SqlDbType.VarBinary, -1).Value = company.LogoBytes;
                command.ExecuteNonQuery();
            }
        }

        private void SaveModules(SqlConnection connection, SqlTransaction transaction, Company company)
        {
            using (var deleteCommand = new SqlCommand("dbo.uspModules_DeleteByCompany", connection, transaction))
            {
                deleteCommand.CommandType = CommandType.StoredProcedure;
                deleteCommand.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = company.CompanyIdentifier;
                deleteCommand.ExecuteNonQuery();
            }

            foreach (var module in company.Modules)
            {
                using (var command = new SqlCommand("dbo.uspModule_Save", connection, transaction))
                {
                    command.CommandType = CommandType.StoredProcedure;
                    command.Parameters.Add("@CompanyIdentifier", SqlDbType.NVarChar, 50).Value = company.CompanyIdentifier;
                    command.Parameters.Add("@ModuleName", SqlDbType.NVarChar, 100).Value = module.Name;
                    command.Parameters.Add("@IsEnabled", SqlDbType.Bit).Value = module.IsEnabled;
                    command.ExecuteNonQuery();
                }
            }
        }

        private static Company MapCompany(SqlDataReader reader)
        {
            return new Company
            {
                CompanyIdentifier = ReadString(reader, "CompanyIdentifier"),
                CompanyName = ReadString(reader, "CompanyName"),
                Address1 = ReadString(reader, "Address1"),
                Address2 = ReadString(reader, "Address2"),
                City = ReadString(reader, "City"),
                State = ReadString(reader, "State"),
                Zip = ReadString(reader, "Zip"),
                PhoneNumber = ReadString(reader, "PhoneNumber"),
                PrimaryContact = ReadString(reader, "PrimaryContact"),
                PointOfContactEmail = ReadString(reader, "PointOfContactEmail"),
                TaxId = ReadString(reader, "TaxId"),
                BankName = ReadString(reader, "BankName"),
                Form1099 = ReadBoolean(reader, "Form1099"),
                WithholdingNumber = ReadString(reader, "WithholdingNumber"),
                County = ReadString(reader, "County"),
                LogoFileName = ReadString(reader, "LogoFileName"),
                LogoContentType = ReadString(reader, "LogoContentType")
            };
        }

        private static void AddNullable(SqlCommand command, string name, string value, int size)
        {
            var parameter = command.Parameters.Add(name, SqlDbType.NVarChar, size);
            parameter.Value = string.IsNullOrWhiteSpace(value) ? (object)DBNull.Value : value;
        }

        private static string ReadString(SqlDataReader reader, string columnName)
        {
            var ordinal = reader.GetOrdinal(columnName);
            return reader.IsDBNull(ordinal) ? string.Empty : reader.GetString(ordinal);
        }

        private static bool ReadBoolean(SqlDataReader reader, string columnName)
        {
            var ordinal = reader.GetOrdinal(columnName);
            return !reader.IsDBNull(ordinal) && reader.GetBoolean(ordinal);
        }
    }
}
